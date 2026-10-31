from datetime import datetime
from app.extensions import db

class Product(db.Model):
    """
    Product model representing services or physical/digital goods offered for subscription.
    Managed by Nidha's module.
    """
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    variants = db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan', lazy='dynamic')
    invoice_lines = db.relationship('InvoiceLine', backref='product', lazy='dynamic')

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
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    attributes = db.Column(db.JSON, nullable=True)  # Key-value attributes (e.g., {"users": 5, "storage": "100GB"})
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ProductVariant id={self.id} sku='{self.sku}' name='{self.name}'>"
