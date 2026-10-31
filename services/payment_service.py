import uuid
from datetime import datetime, date
from decimal import Decimal
from extensions import db
from models.payment import Payment
from models.invoice import Invoice
from models.user import User

class PaymentValidationError(Exception):
    """Custom exception raised for invalid payment operations."""
    pass

class PaymentService:

    @staticmethod
    def generate_payment_reference():
        """Generates a professional unique payment reference (e.g., PAY-20261031-A1B2)."""
        today_str = date.today().strftime('%Y%m%d')
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"PAY-{today_str}-{unique_suffix}"

    @staticmethod
    def record_payment(invoice_id, amount, payment_method, payment_date=None, notes=None, current_user=None):
        """
        Records a payment against an invoice:
        - Validates invoice existence and confirmed state
        - Validates amount > 0
        - Calculates outstanding balance: Total - Total Valid Payments
        - Enforces overpayment policy: Prevents recording payments that exceed outstanding balance
        - Links payment to invoice and customer
        - Refreshes invoice payment status (unpaid -> partially_paid -> paid / overdue)
        """
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            raise PaymentValidationError(f"Invoice #{invoice_id} not found.")

        if invoice.status == 'cancelled':
            raise PaymentValidationError("Cannot record payments on cancelled invoices.")

        if invoice.status == 'draft':
            raise PaymentValidationError("Cannot record payments on draft invoices. Please confirm invoice first.")

        # Validate amount
        try:
            pay_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
            if pay_amount <= Decimal('0.00'):
                raise PaymentValidationError("Payment amount must be greater than zero.")
        except (ValueError, TypeError):
            raise PaymentValidationError("Invalid payment amount format.")

        # Calculate current outstanding balance
        outstanding = invoice.outstanding_amount

        if outstanding <= Decimal('0.00'):
            raise PaymentValidationError(f"Invoice {invoice.invoice_number} is already fully paid. Outstanding balance is $0.00.")

        # Overpayment prevention
        if pay_amount > outstanding:
            raise PaymentValidationError(
                f"Overpayment blocked: Payment amount (${pay_amount:,.2f}) exceeds outstanding balance (${outstanding:,.2f}) on invoice {invoice.invoice_number}."
            )

        # Parse payment date
        if not payment_date:
            pay_date = date.today()
        elif isinstance(payment_date, str):
            pay_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        else:
            pay_date = payment_date

        # Validate payment method
        valid_methods = ('bank_transfer', 'credit_card', 'cash', 'stripe', 'cheque', 'other')
        if payment_method not in valid_methods:
            raise PaymentValidationError(f"Invalid payment method '{payment_method}'. Allowed: {', '.join(valid_methods)}.")

        # Create payment record
        payment = Payment(
            payment_reference=PaymentService.generate_payment_reference(),
            customer_id=invoice.customer_id,
            invoice_id=invoice.id,
            amount=pay_amount,
            payment_date=pay_date,
            payment_method=payment_method,
            notes=notes.strip() if notes else None
        )

        db.session.add(payment)
        
        # Flush to include new payment in calculations
        db.session.flush()

        # Update invoice payment status correctly
        invoice.refresh_payment_status()

        db.session.commit()
        return payment

    @staticmethod
    def get_payment_history(customer_id=None, method=None, date_from=None, date_to=None, search=None):
        """
        Retrieves payment history with dynamic filters.
        """
        query = Payment.query.join(Invoice).join(User, Payment.customer_id == User.id)

        if customer_id:
            query = query.filter(Payment.customer_id == customer_id)

        if method:
            query = query.filter(Payment.payment_method == method)

        if date_from:
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Payment.payment_date >= date_from)

        if date_to:
            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Payment.payment_date <= date_to)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Payment.payment_reference.ilike(search_term),
                    Invoice.invoice_number.ilike(search_term),
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )

        return query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()

    @staticmethod
    def get_tracked_invoices(status_filter=None, customer_id=None, date_from=None, date_to=None, search=None):
        """
        Retrieves invoices for outstanding and overdue tracking:
        - Accurately excludes fully paid invoices from overdue lists
        - Calculates outstanding amounts dynamically
        - Supports filtering by customer, date range, and payment status
        """
        query = Invoice.query.join(User, Invoice.customer_id == User.id)

        # Exclude draft and cancelled if tracking billing/payments
        query = query.filter(Invoice.status.in_(['confirmed', 'paid']))

        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)

        if date_from:
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Invoice.invoice_date >= date_from)

        if date_to:
            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Invoice.invoice_date <= date_to)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    Invoice.invoice_number.ilike(search_term),
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )

        invoices = query.order_by(Invoice.due_date.asc()).all()

        # Refresh dynamic status for each invoice
        for inv in invoices:
            inv.refresh_payment_status()

        # Apply specific status filters
        today = date.today()
        if status_filter == 'outstanding':
            # Any invoice with outstanding_amount > 0
            return [inv for inv in invoices if inv.outstanding_amount > Decimal('0.00')]
        elif status_filter == 'overdue':
            # Must be past due date, has outstanding balance, and NOT fully paid
            return [inv for inv in invoices if inv.due_date < today and inv.outstanding_amount > Decimal('0.00')]
        elif status_filter == 'paid':
            return [inv for inv in invoices if inv.outstanding_amount == Decimal('0.00')]
        elif status_filter == 'partially_paid':
            return [inv for inv in invoices if inv.total_paid > Decimal('0.00') and inv.outstanding_amount > Decimal('0.00')]
        elif status_filter == 'unpaid':
            return [inv for inv in invoices if inv.total_paid == Decimal('0.00') and inv.outstanding_amount > Decimal('0.00')]

        return invoices
