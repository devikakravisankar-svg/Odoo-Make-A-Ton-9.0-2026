from datetime import datetime
from extensions import db

class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subscription_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    payment_terms = db.Column(db.String(100), default='Immediate Payment', nullable=False)
    
    # State: Draft -> Quotation -> Confirmed -> Active -> Closed
    status = db.Column(
        db.Enum('draft', 'quotation', 'confirmed', 'active', 'closed', name='sub_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    is_paused = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    invoices = db.relationship('Invoice', backref='subscription', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'subscription_number': self.subscription_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'plan_id': self.plan_id,
            'plan_name': self.plan.name if self.plan else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'payment_terms': self.payment_terms,
            'status': self.status,
            'is_paused': self.is_paused
        }
