from datetime import date
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.subscription import Subscription
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.utils.decorators import staff_required, admin_required
from app.utils.validators import validate_password_strength

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
@staff_required
def index():
    """
    Main responsive admin/staff dashboard.
    Computes all statistics in real-time from the database.
    """
    # 1. Total customers
    total_customers = User.query.filter_by(role=User.ROLE_CUSTOMER).count()

    # 2. Active subscriptions
    active_subscriptions = Subscription.query.filter_by(status=Subscription.STATUS_ACTIVE).count()

    # 3. Revenue received (sum of successful payments)
    revenue_received = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0.0)
    ).filter(Payment.status == Payment.STATUS_SUCCESSFUL).scalar()

    # 4. Outstanding invoices (pending or partially paid)
    outstanding_invoices_count = Invoice.query.filter(
        Invoice.status.in_([Invoice.STATUS_PENDING, Invoice.STATUS_PARTIALLY_PAID])
    ).count()

    outstanding_invoices_amount = db.session.query(
        func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid), 0.0)
    ).filter(
        Invoice.status.in_([Invoice.STATUS_PENDING, Invoice.STATUS_PARTIALLY_PAID])
    ).scalar()

    # 5. Overdue invoices
    today = date.today()
    overdue_invoices_count = Invoice.query.filter(
        (Invoice.status == Invoice.STATUS_OVERDUE) |
        (
            (Invoice.due_date < today) &
            (~Invoice.status.in_([Invoice.STATUS_PAID, Invoice.STATUS_CANCELLED]))
        )
    ).count()

    # 6. Recent activities
    recent_subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).limit(5).all()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    recent_payments = Payment.query.order_by(Payment.transaction_date.desc()).limit(5).all()

    return render_template(
        'dashboard/index.html',
        total_customers=total_customers,
        active_subscriptions=active_subscriptions,
        revenue_received=revenue_received,
        outstanding_invoices_count=outstanding_invoices_count,
        outstanding_invoices_amount=outstanding_invoices_amount,
        overdue_invoices_count=overdue_invoices_count,
        recent_subscriptions=recent_subscriptions,
        recent_invoices=recent_invoices,
        recent_payments=recent_payments
    )


@dashboard_bp.route('/staff')
@login_required
@admin_required
def staff_list():
    """List internal staff accounts. Accessible by Admin only."""
    staff_members = User.query.filter_by(role=User.ROLE_STAFF).order_by(User.created_at.desc()).all()
    return render_template('dashboard/staff_list.html', staff_members=staff_members)


@dashboard_bp.route('/staff/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_staff():
    """
    Create a new Internal Staff member.
    Enforces permission: ONLY Admin can create staff accounts.
    """
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not full_name or not username or not email or not password:
            flash("All required fields must be filled.", "danger")
            return render_template('dashboard/create_staff.html')

        is_strong, msg = validate_password_strength(password)
        if not is_strong:
            flash(msg, "danger")
            return render_template('dashboard/create_staff.html')

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "warning")
            return render_template('dashboard/create_staff.html')

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return render_template('dashboard/create_staff.html')

        new_staff = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone if phone else None,
            role=User.ROLE_STAFF,
            is_active=True
        )
        new_staff.set_password(password)

        db.session.add(new_staff)
        db.session.commit()

        flash(f"Staff account for {full_name} successfully created!", "success")
        return redirect(url_for('dashboard.staff_list'))

    return render_template('dashboard/create_staff.html')
