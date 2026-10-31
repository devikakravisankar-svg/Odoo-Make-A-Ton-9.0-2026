from datetime import datetime
from app.extensions import db

class Tax(db.Model):
    """
    Tax rates applicable to products, subscriptions and invoices (e.g. GST, VAT).
    Managed by Fairooz's module.
    """
    __tablename__ = 'taxes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    rate_percentage = db.Column(db.Numeric(5, 2), nullable=False)  # e.g., 18.00
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Tax id={self.id} name='{self.name}' rate={self.rate_percentage}%>"
