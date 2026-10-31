"""
Module: Product Management & Subscription Plans
Assigned Member: Nidha
Models in scope: Product, ProductVariant, SubscriptionPlan
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.extensions import db
from app.models.product import Product, ProductVariant
from app.models.plan import SubscriptionPlan
from app.utils.decorators import staff_required

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/')
@login_required
@staff_required
def index():
    """List products and plans for administration. Handled by Nidha."""
    products = Product.query.order_by(Product.created_at.desc()).all()
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.created_at.desc()).all()
    return render_template('products/index.html', products=products, plans=plans)
