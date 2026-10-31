from datetime import datetime, date
from decimal import Decimal
from extensions import db

class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    invoice_date = db.Column(db.Date, default=date.today, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    
    subtotal = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    
    # State: Draft -> Confirmed -> Paid (or Cancelled)
    status = db.Column(
        db.Enum('draft', 'confirmed', 'paid', 'cancelled', name='invoice_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    # Payment status: unpaid, partially_paid, paid, overdue
    payment_status = db.Column(
        db.Enum('unpaid', 'partially_paid', 'paid', 'overdue', name='invoice_payment_status_enum'),
        default='unpaid',
        nullable=False,
        index=True
    )
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lines = db.relationship('InvoiceLine', backref='invoice', cascade='all, delete-orphan', lazy=True)
    payments = db.relationship('Payment', backref='invoice', lazy=True, order_by='Payment.payment_date.desc()')
    applied_discounts = db.relationship('InvoiceDiscount', backref='invoice', cascade='all, delete-orphan', lazy=True)

    @property
    def total_paid(self):
        """Calculates total valid payments recorded against this invoice dynamically."""
        from models.payment import Payment
        paid = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0.00))\
                         .filter(Payment.invoice_id == self.id).scalar()
        return Decimal(str(paid or 0.00))

    @property
    def outstanding_amount(self):
        """Outstanding Amount = Invoice Total - Total Valid Payments."""
        total = self.total_amount or Decimal('0.00')
        paid = self.total_paid
        remaining = total - paid
        return max(Decimal('0.00'), remaining)

    @property
    def is_past_due(self):
        """Checks if invoice is past due date and has positive outstanding balance."""
        if self.status == 'cancelled' or self.payment_status == 'paid':
            return False
        if self.outstanding_amount <= Decimal('0.00'):
            return False
        return date.today() > self.due_date

    def refresh_payment_status(self):
        """
        Dynamically updates payment_status:
        - Paid: total_paid >= total_amount
        - Overdue: past due date with remaining balance
        - Partially Paid: 0 < total_paid < total_amount
        - Unpaid: total_paid == 0
        """
        paid = self.total_paid
        total = self.total_amount or Decimal('0.00')
        
        if total > Decimal('0.00') and paid >= total:
            self.payment_status = 'paid'
            if self.status != 'cancelled':
                self.status = 'paid'
        elif self.is_past_due:
            self.payment_status = 'overdue'
        elif paid > Decimal('0.00'):
            self.payment_status = 'partially_paid'
        else:
            self.payment_status = 'unpaid'

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'subscription_id': self.subscription_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'total_paid': float(self.total_paid),
            'outstanding_amount': float(self.outstanding_amount),
            'status': self.status,
            'payment_status': self.payment_status,
            'is_overdue': self.is_past_due
        }
