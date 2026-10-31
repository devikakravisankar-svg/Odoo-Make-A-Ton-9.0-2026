from datetime import datetime
from extensions import db

class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    billing_interval = db.Column(
        db.Enum('daily', 'weekly', 'monthly', 'yearly', name='plan_interval_enum'),
        default='monthly',
        nullable=False
    )
    cost = db.Column(db.Numeric(10, 2), nullable=False)
    min_quantity = db.Column(db.Integer, default=1, nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    
    # Lifecycle controls configured plan by plan
    auto_close = db.Column(db.Boolean, default=False, nullable=False)
    can_close_early = db.Column(db.Boolean, default=True, nullable=False)
    can_pause = db.Column(db.Boolean, default=True, nullable=False)
    can_renew = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscriptions = db.relationship('Subscription', backref='plan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'billing_interval': self.billing_interval,
            'cost': float(self.cost),
            'min_quantity': self.min_quantity,
            'auto_close': self.auto_close,
            'can_pause': self.can_pause,
            'can_renew': self.can_renew
        }
