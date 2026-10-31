from datetime import datetime
from app.extensions import db

class SubscriptionPlan(db.Model):
    """
    SubscriptionPlan defining recurring billing cycles, prices, and terms.
    Managed by Nidha's module.
    """
    __tablename__ = 'subscription_plans'

    INTERVAL_DAILY = 'daily'
    INTERVAL_WEEKLY = 'weekly'
    INTERVAL_MONTHLY = 'monthly'
    INTERVAL_QUARTERLY = 'quarterly'
    INTERVAL_YEARLY = 'yearly'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    billing_interval = db.Column(db.String(20), default=INTERVAL_MONTHLY, nullable=False)
    interval_count = db.Column(db.Integer, default=1, nullable=False)  # Every 1 month, 3 months, etc.
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    trial_days = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    subscriptions = db.relationship('Subscription', foreign_keys='Subscription.plan_id', lazy='dynamic', overlaps='plan')

    def __repr__(self) -> str:
        return f"<SubscriptionPlan id={self.id} code='{self.code}' name='{self.name}'>"
