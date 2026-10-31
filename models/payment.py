from datetime import datetime, date
from extensions import db

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    payment_reference = db.Column(db.String(64), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, default=date.today, nullable=False)
    payment_method = db.Column(
        db.Enum('bank_transfer', 'credit_card', 'cash', 'stripe', 'cheque', 'other', name='payment_method_enum'),
        default='bank_transfer',
        nullable=False
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'payment_reference': self.payment_reference,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'invoice_id': self.invoice_id,
            'invoice_number': self.invoice.invoice_number if self.invoice else None,
            'amount': float(self.amount),
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
