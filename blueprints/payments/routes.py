from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import date
from extensions import db
from models.payment import Payment
from models.invoice import Invoice
from models.user import User
from services.payment_service import PaymentService, PaymentValidationError
from utils.auth_helper import get_current_user

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
def dashboard():
    """Payment management dashboard with recent payments and active invoices needing collection."""
    current_user = get_current_user()
    recent_payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).limit(10).all()
    
    # Invoices needing payment (unpaid or partially paid)
    all_invoices = Invoice.query.filter(Invoice.status.in_(['confirmed'])).all()
    unpaid_invoices = [inv for inv in all_invoices if inv.outstanding_amount > 0]

    return render_template(
        'billing/payment_management.html',
        recent_payments=recent_payments,
        unpaid_invoices=unpaid_invoices,
        current_user=current_user
    )

@payments_bp.route('/record', methods=['GET', 'POST'])
def record_payment():
    """Record a payment against a confirmed invoice with overpayment prevention."""
    current_user = get_current_user()
    preselected_invoice_id = request.args.get('invoice_id', type=int)

    # Invoices available for payment (only confirmed invoices with outstanding balance > 0)
    confirmed_invoices = Invoice.query.filter(Invoice.status == 'confirmed').order_by(Invoice.due_date.asc()).all()
    payable_invoices = [inv for inv in confirmed_invoices if inv.outstanding_amount > 0]

    if request.method == 'POST':
        invoice_id = request.form.get('invoice_id', type=int)
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        payment_date = request.form.get('payment_date')
        notes = request.form.get('notes')

        try:
            payment = PaymentService.record_payment(
                invoice_id=invoice_id,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date,
                notes=notes,
                current_user=current_user
            )
            flash(f"Payment {payment.payment_reference} of ${payment.amount:,.2f} recorded successfully!", 'success')
            return redirect(url_for('payments.payment_history'))
        except PaymentValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f"Error recording payment: {str(e)}", 'danger')

    return render_template(
        'billing/record_payment.html',
        payable_invoices=payable_invoices,
        preselected_invoice_id=preselected_invoice_id,
        current_user=current_user,
        today=date.today().isoformat()
    )

@payments_bp.route('/history')
def payment_history():
    """Full searchable and filterable payment history."""
    current_user = get_current_user()
    customer_id = request.args.get('customer_id', type=int)
    method = request.args.get('method')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search', '').strip()

    customers = User.query.filter_by(role='customer').all()
    payments = PaymentService.get_payment_history(
        customer_id=customer_id,
        method=method,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

    total_recorded_amount = sum((p.amount for p in payments), 0)

    return render_template(
        'billing/payment_history.html',
        payments=payments,
        customers=customers,
        current_user=current_user,
        total_recorded_amount=total_recorded_amount,
        customer_id=customer_id,
        method=method,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

@payments_bp.route('/api/invoice/<int:invoice_id>/balance')
def api_invoice_balance(invoice_id):
    """API endpoint providing real-time balance calculations for Vanilla JS dynamic UI."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    invoice.refresh_payment_status()
    return jsonify({
        'invoice_id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'customer_name': invoice.customer.name if invoice.customer else 'Unknown',
        'total_amount': float(invoice.total_amount),
        'total_paid': float(invoice.total_paid),
        'outstanding_amount': float(invoice.outstanding_amount),
        'due_date': invoice.due_date.isoformat(),
        'is_overdue': invoice.is_past_due,
        'payment_status': invoice.payment_status
    })
