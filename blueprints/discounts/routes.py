from flask import Blueprint, render_template, request, abort
from datetime import date
from extensions import db
from models.invoice import Invoice
from models.user import User
from models.discount import Discount
from services.payment_service import PaymentService
from services.discount_service import DiscountService
from utils.auth_helper import get_current_user

invoices_bp = Blueprint('tracked_invoices', __name__, url_prefix='/invoices')

@invoices_bp.route('/<int:invoice_id>')
def invoice_detail(invoice_id):
    """
    Detailed Invoice View:
    Displays line items, applied discounts, payment history, outstanding balance,
    and allows applying eligible discounts or recording payments.
    """
    current_user = get_current_user()
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.refresh_payment_status()

    eligible_discounts = DiscountService.get_eligible_discounts_for_invoice(invoice)

    return render_template(
        'billing/invoice_detail.html',
        invoice=invoice,
        eligible_discounts=eligible_discounts,
        current_user=current_user,
        today=date.today()
    )

@invoices_bp.route('/outstanding')
def outstanding_invoices():
    """
    Outstanding Invoices Tracking:
    Displays all invoices with an unpaid balance (> 0.00), with filters and summary totals.
    """
    current_user = get_current_user()
    customer_id = request.args.get('customer_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search', '').strip()

    customers = User.query.filter_by(role='customer').all()
    invoices = PaymentService.get_tracked_invoices(
        status_filter='outstanding',
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

    total_outstanding = sum((inv.outstanding_amount for inv in invoices), 0)

    return render_template(
        'billing/outstanding_invoices.html',
        invoices=invoices,
        customers=customers,
        total_outstanding=total_outstanding,
        current_user=current_user,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        today=date.today()
    )

@invoices_bp.route('/overdue')
def overdue_invoices():
    """
    Overdue Invoices Tracking:
    Displays invoices that are past their due date AND still have an unpaid balance.
    Fully paid invoices are strictly excluded.
    """
    current_user = get_current_user()
    customer_id = request.args.get('customer_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search', '').strip()

    customers = User.query.filter_by(role='customer').all()
    invoices = PaymentService.get_tracked_invoices(
        status_filter='overdue',
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

    total_overdue = sum((inv.outstanding_amount for inv in invoices), 0)

    return render_template(
        'billing/overdue_invoices.html',
        invoices=invoices,
        customers=customers,
        total_overdue=total_overdue,
        current_user=current_user,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        today=date.today()
    )
