from datetime import datetime
from extensions import db

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    product_type = db.Column(db.String(50), default='software', nullable=False)  # software, service, add-on
    sales_price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    variants = db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan', lazy=True)
    invoice_lines = db.relationship('InvoiceLine', backref='product', lazy=True)
    discounts = db.relationship('Discount', backref='applicable_product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'product_type': self.product_type,
            'sales_price': float(self.sales_price),
            'cost_price': float(self.cost_price),
            'notes': self.notes,
            'is_active': self.is_active
        }

class ProductVariant(db.Model):
    __tablename__ = 'product_variants'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_name = db.Column(db.String(100), nullable=False)  # e.g., 'Odoo Brand', 'Enterprise'
    price_extra = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)  # e.g., 560.00

    def get_effective_price(self):
        return float(self.product.sales_price) + float(self.price_extra)
