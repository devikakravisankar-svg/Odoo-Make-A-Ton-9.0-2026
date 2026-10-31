from datetime import datetime
from app.extensions import db

class Payment(db.Model):
    """
    Payment transaction record linked to Invoices and Customers.
    Managed by Fairooz's module.
    """
    __tablename__ = 'payments'

    STATUS_SUCCESSFUL = 'successful'
    STATUS_PENDING = 'pending'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    METHOD_CARD = 'card'
    METHOD_BANK_TRANSFER = 'bank_transfer'
    METHOD_UPI = 'upi'
    METHOD_CASH = 'cash'

    id = db.Column(db.Integer, primary_key=True)
    payment_reference = db.Column(db.String(64), unique=True, nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(30), default=METHOD_CARD, nullable=False)
    status = db.Column(db.String(20), default=STATUS_SUCCESSFUL, nullable=False, index=True)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Payment id={self.id} ref='{self.payment_reference}' amount={self.amount} status='{self.status}'>"
