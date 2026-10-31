"""
Module: Quotations, Subscriptions & Invoices
Assigned Member: Sridhya
Models in scope: Quotation, Subscription, Invoice, InvoiceLine
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.extensions import db
from app.models.quotation import Quotation
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine
from app.utils.decorators import staff_required

subscriptions_bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')

@subscriptions_bp.route('/')
@login_required
@staff_required
def index():
    """Management view for subscriptions, quotations, and invoices. Handled by Sridhya."""
    subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).all()
    quotations = Quotation.query.order_by(Quotation.created_at.desc()).all()
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template(
        'subscriptions/index.html',
        subscriptions=subscriptions,
        quotations=quotations,
        invoices=invoices
    )
