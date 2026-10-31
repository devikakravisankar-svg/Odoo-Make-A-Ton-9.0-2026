from datetime import datetime, date
from app.extensions import db

class Invoice(db.Model):
    """
    Invoice model representing billing demands for subscriptions.
    Managed by Sridhya's module.
    """
    __tablename__ = 'invoices'

    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_PARTIALLY_PAID = 'partially_paid'
    STATUS_OVERDUE = 'overdue'
    STATUS_CANCELLED = 'cancelled'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True, index=True)
    issue_date = db.Column(db.Date, default=date.today, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False, index=True)
    subtotal = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    lines = db.relationship('InvoiceLine', backref='invoice', cascade='all, delete-orphan', lazy='dynamic')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic')

    @property
    def balance_due(self):
        return float(self.total_amount) - float(self.amount_paid)

    @property
    def is_overdue(self):
        if self.status in (self.STATUS_PAID, self.STATUS_CANCELLED):
            return False
        return self.due_date < date.today()

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} num='{self.invoice_number}' total={self.total_amount} status='{self.status}'>"


class InvoiceLine(db.Model):
    """
    InvoiceLine represents detailed line items on an Invoice.
    Managed by Sridhya's module.
    """
    __tablename__ = 'invoice_lines'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    line_total = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)

    def __repr__(self) -> str:
        return f"<InvoiceLine id={self.id} desc='{self.description}' qty={self.quantity} total={self.line_total}>"
