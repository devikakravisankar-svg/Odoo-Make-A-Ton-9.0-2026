from datetime import datetime
from extensions import db

class InvoiceDiscount(db.Model):
    """
    Audit log linking Invoices and Applied Discounts.
    Tracks exact deduction amount applied and prevents duplicate applications.
    """
    __tablename__ = 'invoice_discounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey('discounts.id'), nullable=False)
    applied_amount = db.Column(db.Numeric(10, 2), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint to prevent duplicate application of the same discount to an invoice
    __table_args__ = (
        db.UniqueConstraint('invoice_id', 'discount_id', name='uq_invoice_discount'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'discount_id': self.discount_id,
            'discount_name': self.discount.name if self.discount else None,
            'applied_amount': float(self.applied_amount),
            'applied_at': self.applied_at.isoformat() if self.applied_at else None
        }
