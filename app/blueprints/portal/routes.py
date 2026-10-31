import uuid
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.product import Product
from app.models.plan import SubscriptionPlan
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment
from app.utils.validators import validate_password_strength

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')

@portal_bp.route('/')
@login_required
def index():
    """Customer overview page showing quick summary of active services."""
    active_subscriptions = Subscription.query.filter_by(
        customer_id=current_user.id,
        status=Subscription.STATUS_ACTIVE
    ).all()

    pending_invoices = Invoice.query.filter(
        Invoice.customer_id == current_user.id,
        Invoice.status.in_([Invoice.STATUS_PENDING, Invoice.STATUS_PARTIALLY_PAID])
    ).all()

    recent_payments = Payment.query.filter_by(
        customer_id=current_user.id
    ).order_by(Payment.transaction_date.desc()).limit(5).all()

    return render_template(
        'portal/index.html',
        active_subscriptions=active_subscriptions,
        pending_invoices=pending_invoices,
        recent_payments=recent_payments
    )


@portal_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Customer profile viewing and editing."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()

            if not full_name:
                flash("Full name cannot be empty.", "warning")
            else:
                current_user.full_name = full_name
                current_user.phone = phone if phone else None
                db.session.commit()
                flash("Profile details updated successfully.", "success")

        elif action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pwd):
                flash("Current password is incorrect.", "danger")
            elif new_pwd != confirm_pwd:
                flash("New passwords do not match.", "danger")
            else:
                is_strong, msg = validate_password_strength(new_pwd)
                if not is_strong:
                    flash(msg, "danger")
                else:
                    current_user.set_password(new_pwd)
                    db.session.commit()
                    flash("Password changed successfully.", "success")

        return redirect(url_for('portal.profile'))

    return render_template('portal/profile.html', user=current_user)


@portal_bp.route('/products')
@login_required
def products():
    """Browse available products, product variants, and subscription plans."""
    available_products = Product.query.filter_by(is_active=True).all()
    available_plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    return render_template(
        'portal/products.html',
        products=available_products,
        plans=available_plans
    )


@portal_bp.route('/subscriptions')
@login_required
def subscriptions():
    """
    List subscriptions belonging strictly to the logged-in customer.
    Enforces customer isolation.
    """
    user_subscriptions = Subscription.query.filter_by(
        customer_id=current_user.id
    ).order_by(Subscription.created_at.desc()).all()
    return render_template('portal/subscriptions.html', subscriptions=user_subscriptions)


@portal_bp.route('/invoices')
@login_required
def invoices():
    """
    List invoices belonging strictly to the logged-in customer.
    Enforces customer isolation.
    """
    user_invoices = Invoice.query.filter_by(
        customer_id=current_user.id
    ).order_by(Invoice.issue_date.desc()).all()
    return render_template('portal/invoices.html', invoices=user_invoices)


@portal_bp.route('/invoices/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    """
    View specific invoice details.
    Backend route protection: Customers can only access their own invoices.
    """
    invoice = db.get_or_404(Invoice, invoice_id)
    if invoice.customer_id != current_user.id and not current_user.is_admin_or_staff:
        flash("Unauthorized access: You can only view your own invoices.", "danger")
        abort(403)
    return render_template('portal/invoice_detail.html', invoice=invoice)


@portal_bp.route('/subscribe/<int:plan_id>', methods=['POST'])
@login_required
def subscribe(plan_id):
    """
    Customer action to subscribe to a selected plan.
    Creates a real Subscription and an initial pending Invoice in the database.
    """
    plan = db.session.get(SubscriptionPlan, plan_id)
    if not plan or not plan.is_active:
        flash("The requested subscription plan is not currently available.", "warning")
        return redirect(url_for('portal.products'))

    # Calculate cycle duration
    today = date.today()
    if plan.billing_interval == SubscriptionPlan.INTERVAL_YEARLY:
        next_billing = today + timedelta(days=365)
    elif plan.billing_interval == SubscriptionPlan.INTERVAL_QUARTERLY:
        next_billing = today + timedelta(days=90)
    elif plan.billing_interval == SubscriptionPlan.INTERVAL_WEEKLY:
        next_billing = today + timedelta(days=7)
    else:
        next_billing = today + timedelta(days=30)

    unique_sub_num = f"SUB-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    subscription = Subscription(
        subscription_number=unique_sub_num,
        customer_id=current_user.id,
        plan_id=plan.id,
        status=Subscription.STATUS_ACTIVE,
        start_date=today,
        next_billing_date=next_billing,
        auto_renew=True,
        total_amount=plan.base_price
    )
    db.session.add(subscription)
    db.session.flush()

    # Generate initial invoice
    unique_inv_num = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    tax_amount = round(float(plan.base_price) * 0.18, 2)
    total_amount = round(float(plan.base_price) + tax_amount, 2)

    invoice = Invoice(
        invoice_number=unique_inv_num,
        customer_id=current_user.id,
        subscription_id=subscription.id,
        issue_date=today,
        due_date=today + timedelta(days=7),
        status=Invoice.STATUS_PENDING,
        subtotal=plan.base_price,
        tax_amount=tax_amount,
        discount_amount=0.00,
        total_amount=total_amount,
        amount_paid=0.00
    )
    db.session.add(invoice)
    db.session.flush()

    # Add invoice line item
    line = InvoiceLine(
        invoice_id=invoice.id,
        description=f"Initial Subscription Fee: {plan.name} ({plan.billing_interval})",
        quantity=1,
        unit_price=plan.base_price,
        line_total=plan.base_price
    )
    db.session.add(line)
    db.session.commit()

    flash(f"Successfully subscribed to {plan.name}! Your initial invoice {invoice.invoice_number} is ready for payment.", "success")
    return redirect(url_for('portal.subscriptions'))


@portal_bp.route('/invoices/<int:invoice_id>/pay', methods=['POST'])
@login_required
def pay_invoice(invoice_id):
    """
    Process payment for an invoice.
    Enforces customer isolation and updates invoice status in real-time.
    """
    invoice = db.get_or_404(Invoice, invoice_id)

    if invoice.customer_id != current_user.id and not current_user.is_admin_or_staff:
        flash("Unauthorized payment attempt.", "danger")
        abort(403)

    if invoice.status == Invoice.STATUS_PAID:
        flash("This invoice is already paid in full.", "info")
        return redirect(url_for('portal.invoice_detail', invoice_id=invoice.id))

    payment_method = request.form.get('payment_method', Payment.METHOD_CARD)
    payment_ref = f"PAY-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    due_balance = float(invoice.balance_due)
    if due_balance <= 0:
        due_balance = float(invoice.total_amount)

    payment = Payment(
        payment_reference=payment_ref,
        invoice_id=invoice.id,
        customer_id=current_user.id,
        amount=due_balance,
        payment_method=payment_method,
        status=Payment.STATUS_SUCCESSFUL,
        transaction_date=datetime.utcnow(),
        notes=f"Online payment via {payment_method.upper()}"
    )
    db.session.add(payment)

    # Update invoice paid balance & status
    invoice.amount_paid = float(invoice.amount_paid) + due_balance
    invoice.status = Invoice.STATUS_PAID

    db.session.commit()

    flash(f"Payment of ${due_balance:.2f} processed successfully! Transaction Ref: {payment_ref}", "success")
    return redirect(url_for('portal.invoice_detail', invoice_id=invoice.id))


@portal_bp.route('/payments')
@login_required
def payments():
    """
    List payment transactions belonging strictly to the logged-in customer.
    Enforces customer isolation.
    """
    user_payments = Payment.query.filter_by(
        customer_id=current_user.id
    ).order_by(Payment.transaction_date.desc()).all()
    return render_template('portal/payments.html', payments=user_payments)
