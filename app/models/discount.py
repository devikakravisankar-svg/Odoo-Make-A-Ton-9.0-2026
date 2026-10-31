from datetime import datetime, date
from app.extensions import db

class Discount(db.Model):
    """
    Discount / Coupon model.
    Note: As per project rules, only Admin users have permission to create Discount rules.
    Managed by Fairooz's module.
    """
    __tablename__ = 'discounts'

    TYPE_PERCENTAGE = 'percentage'
    TYPE_FIXED = 'fixed'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    discount_type = db.Column(db.String(20), default=TYPE_PERCENTAGE, nullable=False)
    value = db.Column(db.Numeric(10, 2), nullable=False)  # 15.00 for 15% or $15 fixed
    min_purchase_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    valid_from = db.Column(db.Date, nullable=True)
    valid_until = db.Column(db.Date, nullable=True)
    usage_limit = db.Column(db.Integer, nullable=True)  # Null indicates unlimited
    times_used = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Admin creator
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_valid_now(self):
        if not self.is_active:
            return False
        today = date.today()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False
        return True

    def __repr__(self) -> str:
        return f"<Discount id={self.id} code='{self.code}' value={self.value}>"
