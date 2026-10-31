"""
Module: Quotations, Subscriptions & Invoices
Assigned Member: Sridhya
Blueprint: subscriptions (url_prefix /subscriptions)

Covers:
  /subscriptions/                        — Hub dashboard
  /subscriptions/quotations/             — Quotation list
  /subscriptions/quotations/create       — Create quotation
  /subscriptions/quotations/<id>         — View quotation
  /subscriptions/quotations/<id>/edit    — Edit quotation
  /subscriptions/quotations/<id>/confirm — Confirm → create subscription
  /subscriptions/quotations/<id>/cancel  — Cancel quotation
  /subscriptions/quotations/expire-check — Expire past-validity quotations

  /subscriptions/list                    — Subscription list
  /subscriptions/<id>                    — Subscription detail
  /subscriptions/<id>/activate           — Activate subscription
  /subscriptions/<id>/pause              — Pause subscription
  /subscriptions/<id>/resume             — Resume subscription
  /subscriptions/<id>/close              — Close subscription
  /subscriptions/<id>/renew              — Renew subscription
  /subscriptions/generate-invoices       — Manual invoice generation trigger

  /subscriptions/invoices/               — Invoice list
  /subscriptions/invoices/<id>           — Invoice detail
  /subscriptions/invoices/<id>/confirm   — Confirm invoice
  /subscriptions/invoices/<id>/cancel    — Cancel invoice
  /subscriptions/invoices/<id>/pay       — Mark paid
  /subscriptions/invoices/<id>/print     — Print view
  /subscriptions/invoices/<id>/send      — Send by email
"""

from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.quotation import Quotation, QuotationLine
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine
from app.models.user import User
from app.models.product import Product
from app.models.plan import SubscriptionPlan
from app.models.tax import Tax
from app.utils.decorators import staff_required, admin_required
from app.blueprints.subscriptions.billing import generate_due_invoices, create_invoice_for_period, calculate_billing_period

subscriptions_bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _gen_quotation_number():
    today = date.today().strftime('%Y%m%d')
    prefix = f"QUO-{today}-"
    last = Quotation.query.filter(Quotation.quotation_number.like(f"{prefix}%"))\
                          .order_by(Quotation.id.desc()).first()
    seq = (int(last.quotation_number.split('-')[-1]) + 1) if last else 1
    return f"{prefix}{seq:04d}"


def _gen_subscription_number():
    today = date.today().strftime('%Y%m%d')
    prefix = f"SUB-{today}-"
    last = Subscription.query.filter(Subscription.subscription_number.like(f"{prefix}%"))\
                              .order_by(Subscription.id.desc()).first()
    seq = (int(last.subscription_number.split('-')[-1]) + 1) if last else 1
    return f"{prefix}{seq:04d}"


def _gen_invoice_number():
    today = date.today().strftime('%Y%m%d')
    prefix = f"INV-{today}-"
    last = Invoice.query.filter(Invoice.invoice_number.like(f"{prefix}%"))\
                        .order_by(Invoice.id.desc()).first()
    seq = (int(last.invoice_number.split('-')[-1]) + 1) if last else 1
    return f"{prefix}{seq:04d}"


def _context_dropdowns():
    """Return common dropdown data for forms."""
    return {
        'customers': User.query.filter_by(role=User.ROLE_CUSTOMER, is_active=True).order_by(User.full_name).all(),
        'products': Product.query.filter_by(is_active=True).order_by(Product.name).all(),
        'plans': SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.name).all(),
        'taxes': Tax.query.filter_by(is_active=True).order_by(Tax.name).all(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Hub dashboard
# ─────────────────────────────────────────────────────────────────────────────

@subscriptions_bp.route('/')
@login_required
@staff_required
def index():
    """Hub dashboard showing summary counts and recent activity."""
    quotation_counts = {
        'draft': Quotation.query.filter_by(status=Quotation.STATUS_DRAFT).count(),
        'sent': Quotation.query.filter_by(status=Quotation.STATUS_SENT).count(),
        'confirmed': Quotation.query.filter_by(status=Quotation.STATUS_CONFIRMED).count(),
    }
    subscription_counts = {
        'active': Subscription.query.filter_by(status=Subscription.STATUS_ACTIVE).count(),
        'paused': Subscription.query.filter_by(status=Subscription.STATUS_PAUSED).count(),
        'confirmed': Subscription.query.filter_by(status=Subscription.STATUS_CONFIRMED).count(),
    }
    invoice_counts = {
        'draft': Invoice.query.filter_by(status=Invoice.STATUS_DRAFT).count(),
        'confirmed': Invoice.query.filter_by(status=Invoice.STATUS_CONFIRMED).count(),
        'paid': Invoice.query.filter_by(status=Invoice.STATUS_PAID).count(),
    }
    recent_quotations = Quotation.query.order_by(Quotation.created_at.desc()).limit(5).all()
    recent_subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).limit(5).all()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    overdue_count = Invoice.query.filter(
        Invoice.status.in_([Invoice.STATUS_CONFIRMED, Invoice.STATUS_PENDING]),
        Invoice.due_date < date.today()
    ).count()
    return render_template(
        'subscriptions/index.html',
        quotation_counts=quotation_counts,
        subscription_counts=subscription_counts,
        invoice_counts=invoice_counts,
        recent_quotations=recent_quotations,
        recent_subscriptions=recent_subscriptions,
        recent_invoices=recent_invoices,
        overdue_count=overdue_count,
    )


# ─────────────────────────────────────────────────────────────────────────────
# QUOTATION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@subscriptions_bp.route('/quotations/')
@login_required
@staff_required
def quotation_list():
    status_filter = request.args.get('status', '')
    q = Quotation.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    quotations = q.order_by(Quotation.created_at.desc()).all()
    return render_template('subscriptions/quotations/list.html',
                           quotations=quotations,
                           status_filter=status_filter,
                           all_statuses=Quotation.ALL_STATUSES)


@subscriptions_bp.route('/quotations/create', methods=['GET', 'POST'])
@login_required
@staff_required
def quotation_create():
    ctx = _context_dropdowns()
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        valid_until_str = request.form.get('valid_until', '').strip()
        notes = request.form.get('notes', '').strip()

        if not customer_id:
            flash('Please select a customer.', 'danger')
            return render_template('subscriptions/quotations/create.html', **ctx)

        valid_until = None
        if valid_until_str:
            try:
                valid_until = date.fromisoformat(valid_until_str)
            except ValueError:
                flash('Invalid validity date format.', 'danger')
                return render_template('subscriptions/quotations/create.html', **ctx)

        # Parse line items from form
        product_ids = request.form.getlist('product_id[]')
        plan_ids = request.form.getlist('plan_id[]')
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        tax_ids = request.form.getlist('tax_id[]')

        if not descriptions or not any(d.strip() for d in descriptions):
            flash('Add at least one line item.', 'danger')
            return render_template('subscriptions/quotations/create.html', **ctx)

        quotation = Quotation(
            quotation_number=_gen_quotation_number(),
            customer_id=customer_id,
            created_by_id=current_user.id,
            valid_until=valid_until,
            notes=notes,
            status=Quotation.STATUS_DRAFT,
        )
        db.session.add(quotation)
        db.session.flush()

        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            line = QuotationLine(
                quotation_id=quotation.id,
                description=desc.strip(),
                product_id=int(product_ids[i]) if product_ids[i] else None,
                plan_id=int(plan_ids[i]) if plan_ids[i] else None,
                tax_id=int(tax_ids[i]) if tax_ids[i] else None,
                quantity=int(quantities[i]) if quantities[i] else 1,
                unit_price=float(unit_prices[i]) if unit_prices[i] else 0.0,
            )
            line.recalculate()
            db.session.add(line)

        db.session.flush()
        quotation.recalculate_totals()
        db.session.commit()
        flash(f'Quotation {quotation.quotation_number} created successfully.', 'success')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation.id))

    return render_template('subscriptions/quotations/create.html', **ctx)


@subscriptions_bp.route('/quotations/<int:quotation_id>')
@login_required
@staff_required
def quotation_detail(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    # Auto-expire check on view
    if quotation.is_expired and quotation.status not in (Quotation.STATUS_EXPIRED, Quotation.STATUS_CANCELLED, Quotation.STATUS_CONFIRMED):
        quotation.status = Quotation.STATUS_EXPIRED
        db.session.commit()
        flash('This quotation has been automatically expired (past validity date).', 'warning')
    lines = quotation.lines.all()
    return render_template('subscriptions/quotations/detail.html',
                           quotation=quotation, lines=lines)


@subscriptions_bp.route('/quotations/<int:quotation_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def quotation_edit(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    if not quotation.can_edit:
        flash('Only draft or sent quotations can be edited.', 'warning')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation_id))

    ctx = _context_dropdowns()
    lines = quotation.lines.all()

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        valid_until_str = request.form.get('valid_until', '').strip()
        notes = request.form.get('notes', '').strip()

        if not customer_id:
            flash('Please select a customer.', 'danger')
            return render_template('subscriptions/quotations/edit.html',
                                   quotation=quotation, lines=lines, **ctx)

        valid_until = None
        if valid_until_str:
            try:
                valid_until = date.fromisoformat(valid_until_str)
            except ValueError:
                flash('Invalid validity date format.', 'danger')
                return render_template('subscriptions/quotations/edit.html',
                                       quotation=quotation, lines=lines, **ctx)

        quotation.customer_id = customer_id
        quotation.valid_until = valid_until
        quotation.notes = notes

        # Delete old lines and re-create
        for old_line in lines:
            db.session.delete(old_line)
        db.session.flush()

        product_ids = request.form.getlist('product_id[]')
        plan_ids = request.form.getlist('plan_id[]')
        descriptions = request.form.getlist('description[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        tax_ids = request.form.getlist('tax_id[]')

        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            line = QuotationLine(
                quotation_id=quotation.id,
                description=desc.strip(),
                product_id=int(product_ids[i]) if product_ids[i] else None,
                plan_id=int(plan_ids[i]) if plan_ids[i] else None,
                tax_id=int(tax_ids[i]) if tax_ids[i] else None,
                quantity=int(quantities[i]) if quantities[i] else 1,
                unit_price=float(unit_prices[i]) if unit_prices[i] else 0.0,
            )
            line.recalculate()
            db.session.add(line)

        db.session.flush()
        quotation.recalculate_totals()
        db.session.commit()
        flash(f'Quotation {quotation.quotation_number} updated.', 'success')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation.id))

    return render_template('subscriptions/quotations/edit.html',
                           quotation=quotation, lines=lines, **ctx)


@subscriptions_bp.route('/quotations/<int:quotation_id>/confirm', methods=['POST'])
@login_required
@staff_required
def quotation_confirm(quotation_id):
    """Confirm a quotation → automatically creates a Subscription in 'confirmed' state."""
    quotation = Quotation.query.get_or_404(quotation_id)
    if not quotation.can_confirm:
        flash('Only draft or sent quotations can be confirmed.', 'warning')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation_id))
    if quotation.is_expired:
        flash('Cannot confirm an expired quotation.', 'danger')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation_id))

    lines = quotation.lines.all()
    if not lines:
        flash('Cannot confirm a quotation with no line items.', 'danger')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation_id))

    # Use first line's product/plan/tax for the subscription
    first_line = lines[0]
    start_date = date.today()
    plan = first_line.plan
    end_date = None
    next_billing = start_date
    if plan:
        _, period_end = calculate_billing_period(
            type('obj', (object,), {
                'plan': plan,
                'next_billing_date': start_date,
                'end_date': None,
            })()
        )
        end_date = None  # open-ended by default; admin can set
        next_billing = start_date

    sub = Subscription(
        subscription_number=_gen_subscription_number(),
        customer_id=quotation.customer_id,
        quotation_id=quotation.id,
        plan_id=first_line.plan_id,
        product_id=first_line.product_id,
        tax_id=first_line.tax_id,
        status=Subscription.STATUS_CONFIRMED,
        start_date=start_date,
        end_date=end_date,
        next_billing_date=next_billing,
        payment_terms=Subscription.TERMS_NET_30,
        quantity=first_line.quantity,
        unit_price=float(first_line.unit_price),
        auto_renew=True,
    )
    sub.recalculate_totals()

    quotation.status = Quotation.STATUS_CONFIRMED
    db.session.add(sub)
    db.session.add(quotation)
    db.session.commit()

    flash(f'Quotation confirmed. Subscription {sub.subscription_number} created.', 'success')
    return redirect(url_for('subscriptions.subscription_detail', subscription_id=sub.id))


@subscriptions_bp.route('/quotations/<int:quotation_id>/cancel', methods=['POST'])
@login_required
@staff_required
def quotation_cancel(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    if quotation.status in (Quotation.STATUS_CONFIRMED, Quotation.STATUS_CANCELLED):
        flash('Cannot cancel a confirmed or already-cancelled quotation.', 'warning')
        return redirect(url_for('subscriptions.quotation_detail', quotation_id=quotation_id))
    quotation.status = Quotation.STATUS_CANCELLED
    db.session.commit()
    flash(f'Quotation {quotation.quotation_number} cancelled.', 'info')
    return redirect(url_for('subscriptions.quotation_list'))


@subscriptions_bp.route('/quotations/expire-check', methods=['POST'])
@login_required
@staff_required
def quotation_expire_check():
    """Manually trigger expiry check for all past-validity quotations."""
    today = date.today()
    expired_count = 0
    candidates = Quotation.query.filter(
        Quotation.valid_until < today,
        Quotation.status.in_([Quotation.STATUS_DRAFT, Quotation.STATUS_SENT])
    ).all()
    for q in candidates:
        q.status = Quotation.STATUS_EXPIRED
        expired_count += 1
    db.session.commit()
    flash(f'Expiry check complete: {expired_count} quotation(s) expired.', 'info')
    return redirect(url_for('subscriptions.quotation_list'))


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@subscriptions_bp.route('/list')
@login_required
@staff_required
def subscription_list():
    status_filter = request.args.get('status', '')
    q = Subscription.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    subscriptions = q.order_by(Subscription.created_at.desc()).all()
    return render_template('subscriptions/list.html',
                           subscriptions=subscriptions,
                           status_filter=status_filter,
                           all_statuses=Subscription.ALL_STATUSES)


@subscriptions_bp.route('/<int:subscription_id>')
@login_required
@staff_required
def subscription_detail(subscription_id):
    sub = Subscription.query.get_or_404(subscription_id)
    # Check for date-based expiry
    if sub.is_expired_by_date:
        sub.status = Subscription.STATUS_EXPIRED
        db.session.commit()
        flash('Subscription has been automatically expired (end date passed).', 'warning')
    invoices = sub.invoices.order_by(Invoice.issue_date.desc()).all()
    return render_template('subscriptions/detail.html',
                           sub=sub,
                           invoices=invoices,
                           today=date.today(),
                           Subscription=Subscription)


@subscriptions_bp.route('/<int:subscription_id>/activate', methods=['POST'])
@login_required
@staff_required
def subscription_activate(subscription_id):
    sub = Subscription.query.get_or_404(subscription_id)
    if not sub.can_transition_to(Subscription.STATUS_ACTIVE):
        flash(f'Cannot activate a subscription in "{sub.status}" state.', 'warning')
        return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))
    sub.status = Subscription.STATUS_ACTIVE
    if not sub.next_billing_date:
        sub.next_billing_date = sub.start_date
    db.session.commit()
    flash(f'Subscription {sub.subscription_number} is now Active.', 'success')
    return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))


@subscriptions_bp.route('/<int:subscription_id>/pause', methods=['POST'])
@login_required
@staff_required
def subscription_pause(subscription_id):
    sub = Subscription.query.get_or_404(subscription_id)
    if not sub.can_transition_to(Subscription.STATUS_PAUSED):
        flash(f'Cannot pause a subscription in "{sub.status}" state.', 'warning')
        return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))
    sub.status = Subscription.STATUS_PAUSED
    sub.paused_at = datetime.utcnow()
    db.session.commit()
    flash(f'Subscription {sub.subscription_number} paused.', 'info')
    return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))


@subscriptions_bp.route('/<int:subscription_id>/resume', methods=['POST'])
@login_required
@staff_required
def subscription_resume(subscription_id):
    sub = Subscription.query.get_or_404(subscription_id)
    if not sub.can_transition_to(Subscription.STATUS_ACTIVE):
        flash(f'Cannot resume a subscription in "{sub.status}" state.', 'warning')
        return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))
    sub.status = Subscription.STATUS_ACTIVE
    sub.paused_at = None
    db.session.commit()
    flash(f'Subscription {sub.subscription_number} resumed.', 'success')
    return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))


@subscriptions_bp.route('/<int:subscription_id>/close', methods=['POST'])
@login_required
@staff_required
def subscription_close(subscription_id):
    sub = Subscription.query.get_or_404(subscription_id)
    if not sub.can_transition_to(Subscription.STATUS_CLOSED):
        flash(f'Cannot close a subscription in "{sub.status}" state.', 'warning')
        return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))
    sub.status = Subscription.STATUS_CLOSED
    sub.closed_at = datetime.utcnow()
    sub.end_date = date.today()
    db.session.commit()
    flash(f'Subscription {sub.subscription_number} closed (early closure).', 'info')
    return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))


@subscriptions_bp.route('/<int:subscription_id>/renew', methods=['POST'])
@login_required
@staff_required
def subscription_renew(subscription_id):
    """Extend subscription end_date by one billing period."""
    sub = Subscription.query.get_or_404(subscription_id)
    if sub.status not in (Subscription.STATUS_ACTIVE, Subscription.STATUS_EXPIRED, Subscription.STATUS_CLOSED):
        flash('Only active, expired or closed subscriptions can be renewed.', 'warning')
        return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))

    extension_months = int(request.form.get('extension_months', 1))
    current_end = sub.end_date or date.today()
    month = current_end.month - 1 + extension_months
    year = current_end.year + month // 12
    month = month % 12 + 1
    import calendar
    day = min(current_end.day, calendar.monthrange(year, month)[1])
    sub.end_date = date(year, month, day)

    if sub.status in (Subscription.STATUS_EXPIRED, Subscription.STATUS_CLOSED):
        sub.status = Subscription.STATUS_ACTIVE
        sub.closed_at = None

    if not sub.next_billing_date or sub.next_billing_date < date.today():
        sub.next_billing_date = date.today()

    db.session.commit()
    flash(f'Subscription {sub.subscription_number} renewed until {sub.end_date}.', 'success')
    return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))


@subscriptions_bp.route('/generate-invoices', methods=['POST'])
@login_required
@staff_required
def generate_invoices():
    """
    Manual trigger to generate all due invoices.
    NOTE: This is the MVP manual trigger. In production, scheduled via APScheduler.
    """
    try:
        created = generate_due_invoices(dry_run=False)
        flash(f'Invoice generation complete. {len(created)} invoice(s) created.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating invoices: {str(e)}', 'danger')
    return redirect(url_for('subscriptions.invoice_list'))


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@subscriptions_bp.route('/invoices/')
@login_required
@staff_required
def invoice_list():
    status_filter = request.args.get('status', '')
    q = Invoice.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    invoices = q.order_by(Invoice.issue_date.desc()).all()
    overdue = [inv for inv in invoices if inv.is_overdue and status_filter == '']
    return render_template('subscriptions/invoices/list.html',
                           invoices=invoices,
                           status_filter=status_filter,
                           all_statuses=Invoice.ALL_STATUSES,
                           overdue_count=len(overdue))


@subscriptions_bp.route('/invoices/<int:invoice_id>')
@login_required
@staff_required
def invoice_detail(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    lines = invoice.lines.all()
    return render_template('subscriptions/invoices/detail.html',
                           invoice=invoice, lines=lines)


@subscriptions_bp.route('/invoices/<int:invoice_id>/confirm', methods=['POST'])
@login_required
@staff_required
def invoice_confirm(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if not invoice.can_confirm:
        flash('Only draft invoices can be confirmed.', 'warning')
        return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))
    invoice.status = Invoice.STATUS_CONFIRMED
    db.session.commit()
    flash(f'Invoice {invoice.invoice_number} confirmed.', 'success')
    return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))


@subscriptions_bp.route('/invoices/<int:invoice_id>/cancel', methods=['POST'])
@login_required
@staff_required
def invoice_cancel(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if not invoice.can_cancel:
        flash('This invoice cannot be cancelled.', 'warning')
        return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))
    # Only admin can cancel confirmed invoices
    if invoice.status == Invoice.STATUS_CONFIRMED and not current_user.is_admin:
        flash('Only administrators can cancel confirmed invoices.', 'danger')
        return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))
    invoice.status = Invoice.STATUS_CANCELLED
    db.session.commit()
    flash(f'Invoice {invoice.invoice_number} cancelled.', 'info')
    return redirect(url_for('subscriptions.invoice_list'))


@subscriptions_bp.route('/invoices/<int:invoice_id>/pay', methods=['POST'])
@login_required
@staff_required
def invoice_pay(invoice_id):
    """Mark invoice as fully paid (manual tracking for MVP)."""
    invoice = Invoice.query.get_or_404(invoice_id)
    if not invoice.can_mark_paid:
        flash('This invoice cannot be marked as paid in its current state.', 'warning')
        return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))
    invoice.status = Invoice.STATUS_PAID
    invoice.amount_paid = invoice.total_amount
    db.session.commit()
    flash(f'Invoice {invoice.invoice_number} marked as Paid.', 'success')
    return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))


@subscriptions_bp.route('/invoices/<int:invoice_id>/print')
@login_required
def invoice_print(invoice_id):
    """Print-friendly invoice view."""
    invoice = Invoice.query.get_or_404(invoice_id)
    # Allow customer to print their own invoice
    if current_user.is_customer and invoice.customer_id != current_user.id:
        abort(403)
    lines = invoice.lines.all()
    return render_template('subscriptions/invoices/print.html',
                           invoice=invoice, lines=lines)


@subscriptions_bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@login_required
@staff_required
def invoice_send(invoice_id):
    """Send invoice by email. Stub for MVP — logs action."""
    invoice = Invoice.query.get_or_404(invoice_id)
    # In production: integrate with app.utils.email_service
    # For MVP: just confirm the action was requested
    flash(
        f'Invoice {invoice.invoice_number} send action triggered. '
        'Configure SMTP in .env to enable actual email delivery.',
        'info'
    )
    return redirect(url_for('subscriptions.invoice_detail', invoice_id=invoice_id))


@subscriptions_bp.route('/invoices/create/<int:subscription_id>', methods=['POST'])
@login_required
@staff_required
def invoice_create_manual(subscription_id):
    """
    Manually create a single invoice for a subscription (for the current billing period).
    Idempotent — will not create a duplicate.
    """
    sub = Subscription.query.get_or_404(subscription_id)
    if sub.status != Subscription.STATUS_ACTIVE:
        flash('Manual invoices can only be created for active subscriptions.', 'warning')
        return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))

    ref_date = sub.next_billing_date or date.today()
    period_start, period_end = calculate_billing_period(sub, ref_date)

    try:
        inv = create_invoice_for_period(sub, period_start, period_end)
        db.session.commit()
        flash(f'Invoice {inv.invoice_number} created for period '
              f'{period_start} – {period_end}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating invoice: {str(e)}', 'danger')

    return redirect(url_for('subscriptions.subscription_detail', subscription_id=subscription_id))
