"""
Shared Database Models for Subscription Management System (Odoo Make-A-Ton 9.0).
Provides centralized exports for all team members (Devika, Nidha, Sridhya, Fairooz).
"""

from app.models.user import User
from app.models.product import Product, ProductVariant
from app.models.plan import SubscriptionPlan
from app.models.quotation import Quotation
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine
from app.models.tax import Tax
from app.models.discount import Discount
from app.models.payment import Payment

__all__ = [
    'User',
    'Product',
    'ProductVariant',
    'SubscriptionPlan',
    'Quotation',
    'Subscription',
    'Invoice',
    'InvoiceLine',
    'Tax',
    'Discount',
    'Payment'
]
