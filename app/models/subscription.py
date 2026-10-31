from datetime import datetime, date
from app.extensions import db

class Subscription(db.Model):
    """
    Subscription model tracking customer subscriptions, cycle dates, and status.
    Managed by Sridhya's module.
    """
    __tablename__ = 'subscriptions'

    STATUS_ACTIVE = 'active'
    STATUS_PENDING = 'pending'
    STATUS_PAUSED = 'paused'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    id = db.Column(db.Integer, primary_key=True)
    subscription_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE, nullable=False, index=True)
    start_date = db.Column(db.Date, default=date.today, nullable=False)
    next_billing_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    auto_renew = db.Column(db.Boolean, default=True, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    invoices = db.relationship('Invoice', backref='subscription', lazy='dynamic')

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} num='{self.subscription_number}' status='{self.status}'>"
