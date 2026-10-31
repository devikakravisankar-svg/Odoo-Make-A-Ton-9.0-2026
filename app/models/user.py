from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(UserMixin, db.Model):
    """
    User model supporting role-based access:
    - 'admin': Full system privileges, staff management, discount creation.
    - 'staff': Operations & records management.
    - 'customer': Portal access to own subscriptions, invoices, and payments.
    """
    __tablename__ = 'users'

    ROLE_ADMIN = 'admin'
    ROLE_STAFF = 'staff'
    ROLE_CUSTOMER = 'customer'
    VALID_ROLES = (ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default=ROLE_CUSTOMER, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    quotations = db.relationship('Quotation', backref='customer', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='customer', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic')
    payments = db.relationship('Payment', backref='customer', lazy='dynamic')
    created_discounts = db.relationship('Discount', backref='creator', lazy='dynamic')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == self.ROLE_ADMIN

    @property
    def is_staff(self) -> bool:
        return self.role == self.ROLE_STAFF

    @property
    def is_customer(self) -> bool:
        return self.role == self.ROLE_CUSTOMER

    @property
    def is_admin_or_staff(self) -> bool:
        return self.role in (self.ROLE_ADMIN, self.ROLE_STAFF)

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
