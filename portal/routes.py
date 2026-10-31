from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.product import Product
from app.models.plan import SubscriptionPlan
from app.models.subscription import Subscription
from app.models.invoice import Invoice
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
