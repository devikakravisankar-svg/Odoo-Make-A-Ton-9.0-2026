from datetime import datetime
from app.extensions import db

class Product(db.Model):
    """
    Product model representing services or physical/digital goods offered for subscription.
    Managed by Nidha's module.
    """
    __tablename__ = 'products'

    TYPE_GOODS = 'goods'
    TYPE_SERVICE = 'service'
    TYPE_SUBSCRIPTION = 'subscription'
    PRODUCT_TYPES = [TYPE_GOODS, TYPE_SERVICE, TYPE_SUBSCRIPTION]

    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'
    STATUS_INACTIVE = 'inactive'
    STATUSES = [STATUS_ACTIVE, STATUS_ARCHIVED, STATUS_INACTIVE]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_type = db.Column(db.String(20), default=TYPE_GOODS, nullable=False)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    cost_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    status = db.Column(db.String(20), default=STATUS_ACTIVE, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    variants = db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan', lazy='dynamic')
    plans = db.relationship('SubscriptionPlan', backref='product', lazy='dynamic')
    invoice_lines = db.relationship('InvoiceLine', backref='product', lazy='dynamic')

    @property
    def sales_price(self):
        """Sales price is base price."""
        return self.base_price

    @sales_price.setter
    def sales_price(self, val):
        self.base_price = val

    @property
    def gross_margin(self):
        """Calculate gross margin between sales price and cost price."""
        sales = float(self.base_price or 0.0)
        cost = float(self.cost_price or 0.0)
        return round(sales - cost, 2)

    @property
    def margin_percentage(self):
        """Calculate gross margin percentage."""
        sales = float(self.base_price or 0.0)
        if sales <= 0:
            return 0.0
        return round((self.gross_margin / sales) * 100, 1)

    def calculate_price(self, variant_id=None):
        """
        Calculate the final product price using the base price and variant price.
        Example: Base price ₹2,000 + Variant additional price ₹560 = Final price ₹2,560.
        """
        base = float(self.base_price or 0.0)
        if not variant_id:
            return round(base, 2)

        variant = ProductVariant.query.filter_by(id=variant_id, product_id=self.id).first()
        if variant:
            extra = float(variant.additional_price if variant.additional_price is not None else (variant.price or 0.0))
            return round(base + extra, 2)
        return round(base, 2)

    def calculate_line_total(self, variant_id=None, quantity=1):
        """
        Calculate the total price for a quotation or invoice line item.
        Formula: Unit Price (Base + Variant Price) * Quantity.
        Validates quantity >= 1.
        """
        qty = max(1, int(quantity))
        unit_price = self.calculate_price(variant_id=variant_id)
        return round(unit_price * qty, 2)

    def get_active_variants(self):
        """Return only active variants for quotation line item pickers."""
        return self.variants.filter_by(is_active=True).all()

    def to_dict(self, include_variants=True):
        data = {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'product_type': self.product_type,
            'sales_price': float(self.base_price or 0.0),
            'cost_price': float(self.cost_price or 0.0),
            'gross_margin': self.gross_margin,
            'margin_percentage': self.margin_percentage,
            'description': self.description or '',
            'notes': self.notes or '',
            'status': self.status,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
        if include_variants:
            data['variants'] = [v.to_dict(include_product=False) for v in self.variants.all()]
        return data

    def __repr__(self) -> str:
        return f"<Product id={self.id} code='{self.code}' name='{self.name}'>"


class ProductVariant(db.Model):
    """
    ProductVariant model for tier/attribute-specific pricing or skus.
    Managed by Nidha's module.
    """
    __tablename__ = 'product_variants'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    variant_name = db.Column(db.String(50), nullable=True)  # Attribute name: e.g. "Size", "Tier"
    variant_value = db.Column(db.String(50), nullable=True) # Option value: e.g. "Large", "Pro"
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)  # Legacy/direct price field
    additional_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)  # Additional variant price
    attributes = db.Column(db.JSON, nullable=True)  # Key-value attributes (e.g., {"users": 5, "storage": "100GB"})
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Synchronize additional_price and price if only one is provided
        if 'additional_price' in kwargs and 'price' not in kwargs:
            self.price = kwargs['additional_price']
        elif 'price' in kwargs and 'additional_price' not in kwargs:
            self.additional_price = kwargs['price']

    def calculate_final_price(self):
        """
        Calculate final price using base product price and additional variant price.
        Formula: Base Sales Price + Additional Variant Price.
        Example: Base ₹2,000 + Variant ₹560 = Final ₹2,560.
        """
        base = float(self.product.base_price if self.product else 0.0)
        extra = float(self.additional_price if self.additional_price is not None else (self.price or 0.0))
        return round(base + extra, 2)

    def to_dict(self, include_product=False):
        data = {
            'id': self.id,
            'product_id': self.product_id,
            'name': self.name,
            'variant_name': self.variant_name or self.name,
            'variant_value': self.variant_value or '',
            'sku': self.sku,
            'additional_price': float(self.additional_price or self.price or 0.0),
            'final_price': self.calculate_final_price(),
            'attributes': self.attributes or {},
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
        if include_product and self.product:
            data['product_name'] = self.product.name
            data['base_sales_price'] = float(self.product.base_price or 0.0)
        return data

    def __repr__(self) -> str:
        return f"<ProductVariant id={self.id} sku='{self.sku}' name='{self.name}'>"
