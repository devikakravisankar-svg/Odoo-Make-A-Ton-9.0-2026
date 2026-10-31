from datetime import datetime, date
from decimal import Decimal
from extensions import db

class Discount(db.Model):
    __tablename__ = 'discounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=True, index=True)
    
    # Types: fixed amount or percentage
    discount_type = db.Column(
        db.Enum('fixed', 'percentage', name='discount_type_enum'),
        nullable=False,
        default='fixed'
    )
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Eligibility conditions
    min_purchase_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    min_quantity = db.Column(db.Integer, default=0, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Usage quotas
    max_usage_limit = db.Column(db.Integer, nullable=True)  # None = unlimited
    current_usage_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Scope: 'product' (specific product) or 'subscription' (whole subscription / invoice)
    scope = db.Column(
        db.Enum('product', 'subscription', name='discount_scope_enum'),
        default='subscription',
        nullable=False
    )
    applicable_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to audit logs
    applied_invoices = db.relationship('InvoiceDiscount', backref='discount', lazy=True)

    @property
    def is_expired(self):
        return date.today() > self.end_date

    @property
    def is_exhausted(self):
        if self.max_usage_limit is None:
            return False
        return self.current_usage_count >= self.max_usage_limit

    @property
    def is_currently_valid(self):
        today = date.today()
        if not self.is_active:
            return False
        if not (self.start_date <= today <= self.end_date):
            return False
        if self.is_exhausted:
            return False
        return True

    def validate_eligibility(self, subtotal, quantity=0, product_id=None, reference_date=None):
        """
        Validates all discount conditions:
        - Active status
        - Temporal validity (start <= date <= end)
        - Usage limit exhaustion
        - Minimum purchase amount
        - Minimum quantity
        - Product scope match
        Returns (bool, str reason)
        """
        check_date = reference_date or date.today()
        
        if not self.is_active:
            return False, "Discount rule is currently inactive."
        
        if check_date < self.start_date:
            return False, f"Discount is not active yet (starts on {self.start_date.isoformat()})."
            
        if check_date > self.end_date:
            return False, f"Discount expired on {self.end_date.isoformat()}."
            
        if self.max_usage_limit is not None and self.current_usage_count >= self.max_usage_limit:
            return False, f"Discount usage limit ({self.max_usage_limit}) has been exhausted."
            
        if Decimal(str(subtotal)) < Decimal(str(self.min_purchase_amount)):
            return False, f"Minimum purchase amount of ${self.min_purchase_amount:,.2f} required (current: ${subtotal:,.2f})."
            
        if int(quantity) < int(self.min_quantity):
            return False, f"Minimum quantity of {self.min_quantity} items required (current: {quantity})."
            
        if self.scope == 'product':
            if product_id is None or int(product_id) != int(self.applicable_product_id):
                return False, f"Discount only applies to product ID {self.applicable_product_id}."

        return True, "Eligible"

    def calculate_discount_amount(self, subtotal):
        """
        Calculates exact discount deduction based on type.
        Ensures discount never exceeds the subtotal itself (cannot drop below zero).
        """
        subtotal_dec = Decimal(str(subtotal))
        if subtotal_dec <= Decimal('0.00'):
            return Decimal('0.00')

        if self.discount_type == 'percentage':
            # Percentage calculation
            pct = Decimal(str(self.discount_value)) / Decimal('100.00')
            calc = (subtotal_dec * pct).quantize(Decimal('0.01'))
        else:
            # Fixed dollar amount
            calc = Decimal(str(self.discount_value)).quantize(Decimal('0.01'))

        # Ensure discount does not exceed subtotal
        return min(calc, subtotal_dec)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value),
            'min_purchase_amount': float(self.min_purchase_amount),
            'min_quantity': self.min_quantity,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'max_usage_limit': self.max_usage_limit,
            'current_usage_count': self.current_usage_count,
            'scope': self.scope,
            'applicable_product_id': self.applicable_product_id,
            'applicable_product_name': self.applicable_product.name if self.applicable_product else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired,
            'is_exhausted': self.is_exhausted,
            'is_currently_valid': self.is_currently_valid
        }
