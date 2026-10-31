from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
from extensions import db
from models.discount import Discount
from models.product import Product
from models.invoice import Invoice
from services.discount_service import DiscountService, DiscountValidationError
from utils.auth_helper import admin_required, get_current_user

discounts_bp = Blueprint('discounts', __name__, url_prefix='/discounts')

@discounts_bp.route('/')
def list_discounts():
    """View discount rules with summary dashboard and filters."""
    current_user = get_current_user()
    scope_filter = request.args.get('scope')
    status_filter = request.args.get('status')
    search = request.args.get('search', '').strip()

    query = Discount.query

    if scope_filter in ('product', 'subscription'):
        query = query.filter(Discount.scope == scope_filter)

    if status_filter == 'active':
        query = query.filter(Discount.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(Discount.is_active == False)
    elif status_filter == 'expired':
        query = query.filter(Discount.end_date < date.today())

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Discount.name.ilike(search_term),
                Discount.code.ilike(search_term)
            )
        )

    discounts = query.order_by(Discount.created_at.desc()).all()

    # Dashboard summary metrics
    total_discounts = Discount.query.count()
    active_discounts = Discount.query.filter_by(is_active=True).count()
    total_redemptions = sum((d.current_usage_count for d in Discount.query.all()), 0)

    return render_template(
        'billing/discount_list.html',
        discounts=discounts,
        current_user=current_user,
        total_discounts=total_discounts,
        active_discounts=active_discounts,
        total_redemptions=total_redemptions,
        current_date=date.today(),
        scope_filter=scope_filter,
        status_filter=status_filter,
        search=search
    )

@discounts_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def new_discount():
    """Create a new discount rule (Admin only)."""
    current_user = get_current_user()
    products = Product.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        try:
            discount = DiscountService.create_discount(request.form, current_user=current_user)
            flash(f"Discount rule '{discount.name}' created successfully!", 'success')
            return redirect(url_for('discounts.list_discounts'))
        except DiscountValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f"Unexpected error creating discount: {str(e)}", 'danger')

    return render_template('billing/discount_form.html', discount=None, products=products, current_user=current_user)

@discounts_bp.route('/<int:discount_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_discount(discount_id):
    """Edit an existing discount rule (Admin only)."""
    current_user = get_current_user()
    discount = Discount.query.get_or_404(discount_id)
    products = Product.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        try:
            DiscountService.update_discount(discount_id, request.form, current_user=current_user)
            flash(f"Discount rule '{discount.name}' updated successfully!", 'success')
            return redirect(url_for('discounts.list_discounts'))
        except DiscountValidationError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f"Unexpected error updating discount: {str(e)}", 'danger')

    return render_template('billing/discount_form.html', discount=discount, products=products, current_user=current_user)

@discounts_bp.route('/<int:discount_id>/toggle', methods=['POST'])
@admin_required
def toggle_discount(discount_id):
    """Enable or disable a discount rule (Admin only)."""
    current_user = get_current_user()
    try:
        discount = DiscountService.toggle_status(discount_id, current_user=current_user)
        state_str = "enabled" if discount.is_active else "disabled"
        flash(f"Discount rule '{discount.name}' has been {state_str}.", 'info')
    except Exception as e:
        flash(str(e), 'danger')
    return redirect(url_for('discounts.list_discounts'))

@discounts_bp.route('/api/apply', methods=['POST'])
def api_apply_discount():
    """
    API endpoint for Sridhya / Invoice Billing Engine to apply a discount to an invoice.
    Payload: { "invoice_id": 123, "discount_id": 45 }
    """
    data = request.get_json() or {}
    invoice_id = data.get('invoice_id')
    discount_id = data.get('discount_id')

    invoice = Invoice.query.get(invoice_id)
    discount = Discount.query.get(discount_id)

    if not invoice or not discount:
        return jsonify({'success': False, 'error': 'Invoice or Discount not found.'}), 404

    try:
        updated_invoice, deduction = DiscountService.apply_discount_to_invoice(invoice, discount)
        return jsonify({
            'success': True,
            'message': f"Discount '{discount.name}' applied successfully.",
            'applied_deduction': float(deduction),
            'new_discount_total': float(updated_invoice.discount_amount),
            'new_invoice_total': float(updated_invoice.total_amount)
        })
    except DiscountValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f"Internal server error: {str(e)}"}), 500
