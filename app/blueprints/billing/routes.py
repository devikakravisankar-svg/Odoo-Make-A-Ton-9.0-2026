"""
Module: Discounts, Payments & Revenue Reports
Assigned Member: Fairooz
Models in scope: Discount, Payment, Tax
Permission Requirement: Only Admin can create discount rules!
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.extensions import db
from app.models.discount import Discount
from app.models.payment import Payment
from app.models.tax import Tax
from app.utils.decorators import staff_required, admin_required

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/')
@login_required
@staff_required
def index():
    """Billing overview showing payments, discounts, and taxes. Handled by Fairooz."""
    payments = Payment.query.order_by(Payment.transaction_date.desc()).all()
    discounts = Discount.query.order_by(Discount.created_at.desc()).all()
    taxes = Tax.query.all()
    return render_template(
        'billing/index.html',
        payments=payments,
        discounts=discounts,
        taxes=taxes
    )
