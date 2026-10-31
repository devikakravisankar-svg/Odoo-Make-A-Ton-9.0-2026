from datetime import datetime, date
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
    INTERVALS = [INTERVAL_DAILY, INTERVAL_WEEKLY, INTERVAL_MONTHLY, INTERVAL_QUARTERLY, INTERVAL_YEARLY]

    RENEWAL_AUTOMATIC = 'automatic'
    RENEWAL_MANUAL = 'manual'
    RENEWAL_NO_RENEWAL = 'no-renewal'
    RENEWAL_SETTINGS = [RENEWAL_AUTOMATIC, RENEWAL_MANUAL, RENEWAL_NO_RENEWAL]

    CLOSURE_PERIOD_END = 'at-period-end'
    CLOSURE_IMMEDIATE = 'immediate'
    CLOSURE_SETTINGS = [CLOSURE_PERIOD_END, CLOSURE_IMMEDIATE]

    STATUS_ACTIVE = 'active'
    STATUS_DISABLED = 'disabled'
    STATUS_ARCHIVED = 'archived'
    STATUSES = [STATUS_ACTIVE, STATUS_DISABLED, STATUS_ARCHIVED]

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    billing_interval = db.Column(db.String(20), default=INTERVAL_MONTHLY, nullable=False)
    interval_count = db.Column(db.Integer, default=1, nullable=False)  # Every 1 day, 1 month, etc.
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    trial_days = db.Column(db.Integer, default=0, nullable=False)
    minimum_quantity = db.Column(db.Integer, default=1, nullable=False)
    start_date = db.Column(db.Date, default=date.today, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    renewal_setting = db.Column(db.String(20), default=RENEWAL_AUTOMATIC, nullable=False)
    closure_setting = db.Column(db.String(20), default=CLOSURE_PERIOD_END, nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    subscriptions = db.relationship('Subscription', backref='plan', lazy='dynamic')

    @property
    def price(self):
        """Price alias for base_price."""
        return self.base_price

    @price.setter
    def price(self, val):
        self.base_price = val

    @property
    def billing_frequency(self):
        """Billing frequency alias for billing_interval."""
        return self.billing_interval

    @billing_frequency.setter
    def billing_frequency(self, val):
        self.billing_interval = val

    def is_currently_available(self, target_date=None) -> bool:
        """
        Validate plan availability.
        A plan is available if status is 'active', is_active is True,
        and target_date is between start_date and end_date (if defined).
        """
        if not self.is_active or self.status != self.STATUS_ACTIVE:
            return False
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                return False
        elif isinstance(target_date, datetime):
            target_date = target_date.date()

        if self.start_date and target_date < self.start_date:
            return False
        if self.end_date and target_date > self.end_date:
            return False
        return True

    def validate_subscription(self, quantity=1, target_date=None):
        """
        Check minimum quantity and date availability.
        Returns (is_valid: bool, error_messages: list[str]).
        """
        errors = []
        if not self.is_currently_available(target_date):
            errors.append(f"Subscription plan '{self.name}' is not currently available for selection.")
        try:
            qty = int(quantity)
            if qty < self.minimum_quantity:
                errors.append(f"Minimum quantity required for plan '{self.name}' is {self.minimum_quantity} (provided: {qty}).")
        except (ValueError, TypeError):
            errors.append("Invalid quantity specified.")
        return (len(errors) == 0, errors)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'name': self.name,
            'code': self.code,
            'description': self.description or '',
            'price': float(self.base_price or 0.0),
            'base_price': float(self.base_price or 0.0),
            'billing_interval': self.billing_interval,
            'billing_frequency': self.billing_interval,
            'interval_count': self.interval_count,
            'trial_days': self.trial_days,
            'minimum_quantity': self.minimum_quantity,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'renewal_setting': self.renewal_setting,
            'closure_setting': self.closure_setting,
            'status': self.status,
            'is_active': self.is_active,
            'is_available': self.is_currently_available(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<SubscriptionPlan id={self.id} code='{self.code}' name='{self.name}'>"
