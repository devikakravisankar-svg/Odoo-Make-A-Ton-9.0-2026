"""
Module: Product Management & Subscription Plans
Assigned Member: Nidha (Member 2)
Models in scope: Product, ProductVariant, SubscriptionPlan
"""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.product import Product, ProductVariant
from app.models.plan import SubscriptionPlan
from app.utils.decorators import staff_required

products_bp = Blueprint('products', __name__, url_prefix='/products')


# ==============================================================================
# 1. PRODUCT MANAGEMENT (CRUD, Search & Filtering)
# ==============================================================================

@products_bp.route('/')
@login_required
@staff_required
def index():
    """
    Products Dashboard.
    Provides metric cards, live filtering by type and status, search, and product table.
    """
    query = Product.query

    # Search filter (name, code, description)
    q = request.args.get('q', '').strip()
    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            (Product.name.ilike(search_filter)) |
            (Product.code.ilike(search_filter)) |
            (Product.description.ilike(search_filter))
        )

    # Type filter
    product_type = request.args.get('type', '').strip()
    if product_type and product_type in Product.PRODUCT_TYPES:
        query = query.filter(Product.product_type == product_type)

    # Status filter
    status = request.args.get('status', '').strip()
    if status and status in Product.STATUSES:
        query = query.filter(Product.status == status)

    # Sort
    sort_by = request.args.get('sort', 'created_desc')
    if sort_by == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort_by == 'price_asc':
        query = query.order_by(Product.base_price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.base_price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.all()

    # Dashboard Statistics
    total_products = Product.query.count()
    active_products = Product.query.filter_by(status=Product.STATUS_ACTIVE).count()
    total_variants = ProductVariant.query.count()
    total_plans = SubscriptionPlan.query.filter_by(status=SubscriptionPlan.STATUS_ACTIVE).count()

    return render_template(
        'products/index.html',
        products=products,
        q=q,
        current_type=product_type,
        current_status=status,
        current_sort=sort_by,
        total_products=total_products,
        active_products=active_products,
        total_variants=total_variants,
        total_plans=total_plans,
        product_types=Product.PRODUCT_TYPES,
        statuses=Product.STATUSES
    )


@products_bp.route('/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_product():
    """Create a new product with comprehensive validation."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        product_type = request.form.get('product_type', Product.TYPE_GOODS).strip()
        sales_price_raw = request.form.get('sales_price', '').strip()
        cost_price_raw = request.form.get('cost_price', '0').strip()
        description = request.form.get('description', '').strip()
        notes = request.form.get('notes', '').strip()
        status = request.form.get('status', Product.STATUS_ACTIVE).strip()

        # Validation
        errors = []
        if not name:
            errors.append('Product name is required.')
        if not code:
            errors.append('Product code/SKU is required.')
        elif Product.query.filter_by(code=code).first():
            errors.append(f"A product with code '{code}' already exists.")

        try:
            sales_price = Decimal(sales_price_raw)
            if sales_price < 0:
                errors.append('Sales price cannot be negative.')
        except (InvalidOperation, ValueError, TypeError):
            errors.append('Invalid sales price entered.')
            sales_price = Decimal('0.00')

        try:
            cost_price = Decimal(cost_price_raw) if cost_price_raw else Decimal('0.00')
            if cost_price < 0:
                errors.append('Cost price cannot be negative.')
        except (InvalidOperation, ValueError, TypeError):
            errors.append('Invalid cost price entered.')
            cost_price = Decimal('0.00')

        if product_type not in Product.PRODUCT_TYPES:
            product_type = Product.TYPE_GOODS

        if status not in Product.STATUSES:
            status = Product.STATUS_ACTIVE

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'products/form.html',
                product=None,
                product_types=Product.PRODUCT_TYPES,
                statuses=Product.STATUSES,
                form_data=request.form
            )

        product = Product(
            name=name,
            code=code,
            product_type=product_type,
            base_price=sales_price,
            cost_price=cost_price,
            description=description,
            notes=notes,
            status=status,
            is_active=(status == Product.STATUS_ACTIVE)
        )
        db.session.add(product)
        db.session.commit()

        flash(f"Product '{product.name}' created successfully.", 'success')
        return redirect(url_for('products.product_detail', id=product.id))

    return render_template(
        'products/form.html',
        product=None,
        product_types=Product.PRODUCT_TYPES,
        statuses=Product.STATUSES,
        form_data={}
    )


@products_bp.route('/<int:id>')
@login_required
@staff_required
def product_detail(id):
    """View product details, attached variants, margins, and plans."""
    product = Product.query.get_or_404(id)
    variants = product.variants.all()
    plans = product.plans.all()
    return render_template(
        'products/details.html',
        product=product,
        variants=variants,
        plans=plans
    )


@products_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_product(id):
    """Edit an existing product."""
    product = Product.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        product_type = request.form.get('product_type', Product.TYPE_GOODS).strip()
        sales_price_raw = request.form.get('sales_price', '').strip()
        cost_price_raw = request.form.get('cost_price', '0').strip()
        description = request.form.get('description', '').strip()
        notes = request.form.get('notes', '').strip()
        status = request.form.get('status', Product.STATUS_ACTIVE).strip()

        errors = []
        if not name:
            errors.append('Product name is required.')
        if not code:
            errors.append('Product code is required.')
        else:
            existing = Product.query.filter_by(code=code).first()
            if existing and existing.id != product.id:
                errors.append(f"A different product with code '{code}' already exists.")

        try:
            sales_price = Decimal(sales_price_raw)
            if sales_price < 0:
                errors.append('Sales price cannot be negative.')
        except (InvalidOperation, ValueError, TypeError):
            errors.append('Invalid sales price entered.')
            sales_price = product.base_price

        try:
            cost_price = Decimal(cost_price_raw) if cost_price_raw else Decimal('0.00')
            if cost_price < 0:
                errors.append('Cost price cannot be negative.')
        except (InvalidOperation, ValueError, TypeError):
            errors.append('Invalid cost price entered.')
            cost_price = product.cost_price

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'products/form.html',
                product=product,
                product_types=Product.PRODUCT_TYPES,
                statuses=Product.STATUSES,
                form_data=request.form
            )

        product.name = name
        product.code = code
        product.product_type = product_type
        product.base_price = sales_price
        product.cost_price = cost_price
        product.description = description
        product.notes = notes
        product.status = status
        product.is_active = (status == Product.STATUS_ACTIVE)
        product.updated_at = datetime.utcnow()

        db.session.commit()
        flash(f"Product '{product.name}' updated successfully.", 'success')
        return redirect(url_for('products.product_detail', id=product.id))

    return render_template(
        'products/form.html',
        product=product,
        product_types=Product.PRODUCT_TYPES,
        statuses=Product.STATUSES,
        form_data={}
    )


@products_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
@staff_required
def toggle_product_status(id):
    """Toggle product status between active and archived."""
    product = Product.query.get_or_404(id)
    if product.status == Product.STATUS_ACTIVE:
        product.status = Product.STATUS_ARCHIVED
        product.is_active = False
        flash(f"Product '{product.name}' archived.", 'info')
    else:
        product.status = Product.STATUS_ACTIVE
        product.is_active = True
        flash(f"Product '{product.name}' reactivated.", 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('products.index'))


@products_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_product(id):
    """Safely delete or archive product if referenced by invoices."""
    product = Product.query.get_or_404(id)

    # Check for downstream references
    if product.invoice_lines.count() > 0:
        product.status = Product.STATUS_ARCHIVED
        product.is_active = False
        db.session.commit()
        flash(f"Product '{product.name}' has associated invoices and was archived instead of deleted.", 'warning')
        return redirect(url_for('products.index'))

    product_name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f"Product '{product_name}' permanently deleted.", 'success')
    return redirect(url_for('products.index'))


# ==============================================================================
# 2. PRODUCT VARIANTS MANAGEMENT
# ==============================================================================

@products_bp.route('/<int:id>/variants')
@login_required
@staff_required
def product_variants(id):
    """Manage product variants and test price calculations."""
    product = Product.query.get_or_404(id)
    variants = product.variants.all()
    return render_template(
        'products/variants.html',
        product=product,
        variants=variants
    )


@products_bp.route('/<int:id>/variants/create', methods=['POST'])
@login_required
@staff_required
def create_variant(id):
    """Add a variant with name, value, SKU, and additional price."""
    product = Product.query.get_or_404(id)

    variant_name = request.form.get('variant_name', '').strip()  # e.g., "Size", "Tier"
    variant_value = request.form.get('variant_value', '').strip() # e.g., "Large", "Pro"
    sku = request.form.get('sku', '').strip().upper()
    additional_price_raw = request.form.get('additional_price', '0.00').strip()

    name = f"{variant_name}: {variant_value}" if (variant_name and variant_value) else (variant_name or variant_value or 'Variant')

    errors = []
    if not variant_name and not name:
        errors.append('Variant name or attribute is required.')

    if not sku:
        sku = f"{product.code}-{variant_value[:4].upper() if variant_value else 'VAR'}"

    # Verify SKU uniqueness
    if ProductVariant.query.filter_by(sku=sku).first():
        errors.append(f"A variant with SKU '{sku}' already exists.")

    try:
        additional_price = Decimal(additional_price_raw)
    except (InvalidOperation, ValueError, TypeError):
        errors.append('Invalid additional price value.')
        additional_price = Decimal('0.00')

    attributes = {}
    if variant_name and variant_value:
        attributes[variant_name] = variant_value

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('products.product_variants', id=product.id))

    variant = ProductVariant(
        product_id=product.id,
        name=name,
        variant_name=variant_name,
        variant_value=variant_value,
        sku=sku,
        price=additional_price,
        additional_price=additional_price,
        attributes=attributes,
        is_active=True
    )
    db.session.add(variant)
    db.session.commit()

    final_price = variant.calculate_final_price()
    flash(
        f"Variant '{variant.name}' added. Base: ₹{float(product.base_price):,.2f} + Additional: ₹{float(variant.additional_price):,.2f} = Final Price: ₹{final_price:,.2f}",
        'success'
    )
    return redirect(url_for('products.product_variants', id=product.id))


@products_bp.route('/<int:id>/variants/<int:variant_id>/edit', methods=['POST'])
@login_required
@staff_required
def edit_variant(id, variant_id):
    """Edit variant name, additional price, and SKU."""
    product = Product.query.get_or_404(id)
    variant = ProductVariant.query.filter_by(id=variant_id, product_id=product.id).first_or_404()

    variant_name = request.form.get('variant_name', '').strip()
    variant_value = request.form.get('variant_value', '').strip()
    sku = request.form.get('sku', '').strip().upper()
    additional_price_raw = request.form.get('additional_price', '0.00').strip()

    errors = []
    if not variant_name and not variant.name:
        errors.append('Variant name is required.')

    if sku and sku != variant.sku:
        existing = ProductVariant.query.filter_by(sku=sku).first()
        if existing and existing.id != variant.id:
            errors.append(f"A variant with SKU '{sku}' already exists.")

    try:
        additional_price = Decimal(additional_price_raw)
    except (InvalidOperation, ValueError, TypeError):
        errors.append('Invalid additional price value.')
        additional_price = variant.additional_price

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('products.product_variants', id=product.id))

    if variant_name:
        variant.variant_name = variant_name
    if variant_value:
        variant.variant_value = variant_value
    variant.name = f"{variant.variant_name}: {variant.variant_value}" if (variant.variant_name and variant.variant_value) else variant.name
    if sku:
        variant.sku = sku
    variant.additional_price = additional_price
    variant.price = additional_price

    db.session.commit()
    flash(f"Variant '{variant.name}' updated successfully.", 'success')
    return redirect(url_for('products.product_variants', id=product.id))


@products_bp.route('/<int:id>/variants/<int:variant_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_variant(id, variant_id):
    """Delete a product variant."""
    product = Product.query.get_or_404(id)
    variant = ProductVariant.query.filter_by(id=variant_id, product_id=product.id).first_or_404()
    variant_name = variant.name

    db.session.delete(variant)
    db.session.commit()
    flash(f"Variant '{variant_name}' removed.", 'info')
    return redirect(url_for('products.product_variants', id=product.id))


# ==============================================================================
# 3. SUBSCRIPTION PLAN MANAGEMENT & OPERATIONS
# ==============================================================================

@products_bp.route('/plans')
@login_required
@staff_required
def plans_list():
    """Subscription plans dashboard with frequency and status filters."""
    query = SubscriptionPlan.query

    # Frequency filter
    interval = request.args.get('interval', '').strip()
    if interval and interval in SubscriptionPlan.INTERVALS:
        query = query.filter(SubscriptionPlan.billing_interval == interval)

    # Status filter
    status = request.args.get('status', '').strip()
    if status and status in SubscriptionPlan.STATUSES:
        query = query.filter(SubscriptionPlan.status == status)

    plans = query.order_by(SubscriptionPlan.created_at.desc()).all()

    # Metrics
    total_plans = SubscriptionPlan.query.count()
    active_plans = SubscriptionPlan.query.filter_by(status=SubscriptionPlan.STATUS_ACTIVE).count()
    monthly_plans = SubscriptionPlan.query.filter_by(billing_interval=SubscriptionPlan.INTERVAL_MONTHLY).count()
    yearly_plans = SubscriptionPlan.query.filter_by(billing_interval=SubscriptionPlan.INTERVAL_YEARLY).count()

    return render_template(
        'products/plans_list.html',
        plans=plans,
        current_interval=interval,
        current_status=status,
        intervals=SubscriptionPlan.INTERVALS,
        statuses=SubscriptionPlan.STATUSES,
        total_plans=total_plans,
        active_plans=active_plans,
        monthly_plans=monthly_plans,
        yearly_plans=yearly_plans
    )


@products_bp.route('/plans/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_plan():
    """Create a new subscription plan with validation."""
    products = Product.query.filter_by(status=Product.STATUS_ACTIVE).order_by(Product.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        product_id = request.form.get('product_id', '').strip()
        description = request.form.get('description', '').strip()
        price_raw = request.form.get('price', '').strip()
        billing_interval = request.form.get('billing_interval', SubscriptionPlan.INTERVAL_MONTHLY).strip()
        interval_count = request.form.get('interval_count', '1').strip()
        trial_days = request.form.get('trial_days', '0').strip()
        minimum_quantity = request.form.get('minimum_quantity', '1').strip()
        start_date_raw = request.form.get('start_date', '').strip()
        end_date_raw = request.form.get('end_date', '').strip()
        renewal_setting = request.form.get('renewal_setting', SubscriptionPlan.RENEWAL_AUTOMATIC).strip()
        closure_setting = request.form.get('closure_setting', SubscriptionPlan.CLOSURE_PERIOD_END).strip()
        status = request.form.get('status', SubscriptionPlan.STATUS_ACTIVE).strip()

        errors = []
        if not name:
            errors.append('Plan name is required.')
        if not code:
            errors.append('Plan code is required.')
        elif SubscriptionPlan.query.filter_by(code=code).first():
            errors.append(f"A subscription plan with code '{code}' already exists.")

        try:
            price = Decimal(price_raw)
            if price < 0:
                errors.append('Price cannot be negative.')
        except (InvalidOperation, ValueError, TypeError):
            errors.append('Invalid plan price entered.')
            price = Decimal('0.00')

        try:
            min_qty = int(minimum_quantity)
            if min_qty < 1:
                errors.append('Minimum quantity must be at least 1.')
        except (ValueError, TypeError):
            errors.append('Invalid minimum quantity.')
            min_qty = 1

        try:
            trials = max(0, int(trial_days))
        except (ValueError, TypeError):
            trials = 0

        try:
            int_count = max(1, int(interval_count))
        except (ValueError, TypeError):
            int_count = 1

        # Dates
        start_date = date.today()
        if start_date_raw:
            try:
                start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Invalid start date format (use YYYY-MM-DD).')

        end_date = None
        if end_date_raw:
            try:
                end_date = datetime.strptime(end_date_raw, '%Y-%m-%d').date()
                if end_date < start_date:
                    errors.append('End date cannot be prior to start date.')
            except ValueError:
                errors.append('Invalid end date format (use YYYY-MM-DD).')

        prod_id = int(product_id) if product_id and product_id.isdigit() else None

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'products/plan_form.html',
                plan=None,
                products=products,
                intervals=SubscriptionPlan.INTERVALS,
                renewal_settings=SubscriptionPlan.RENEWAL_SETTINGS,
                closure_settings=SubscriptionPlan.CLOSURE_SETTINGS,
                statuses=SubscriptionPlan.STATUSES,
                form_data=request.form
            )

        plan = SubscriptionPlan(
            name=name,
            code=code,
            product_id=prod_id,
            description=description,
            base_price=price,
            billing_interval=billing_interval,
            interval_count=int_count,
            trial_days=trials,
            minimum_quantity=min_qty,
            start_date=start_date,
            end_date=end_date,
            renewal_setting=renewal_setting,
            closure_setting=closure_setting,
            status=status,
            is_active=(status == SubscriptionPlan.STATUS_ACTIVE)
        )
        db.session.add(plan)
        db.session.commit()

        flash(f"Subscription plan '{plan.name}' created successfully.", 'success')
        return redirect(url_for('products.plans_list'))

    return render_template(
        'products/plan_form.html',
        plan=None,
        products=products,
        intervals=SubscriptionPlan.INTERVALS,
        renewal_settings=SubscriptionPlan.RENEWAL_SETTINGS,
        closure_settings=SubscriptionPlan.CLOSURE_SETTINGS,
        statuses=SubscriptionPlan.STATUSES,
        form_data={}
    )


@products_bp.route('/plans/<int:id>')
@login_required
@staff_required
def plan_detail(id):
    """View subscription plan details."""
    plan = SubscriptionPlan.query.get_or_404(id)
    return render_template('products/plan_details.html', plan=plan)


@products_bp.route('/plans/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_plan(id):
    """Edit subscription plan details."""
    plan = SubscriptionPlan.query.get_or_404(id)
    products = Product.query.filter_by(status=Product.STATUS_ACTIVE).order_by(Product.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        product_id = request.form.get('product_id', '').strip()
        description = request.form.get('description', '').strip()
        price_raw = request.form.get('price', '').strip()
        billing_interval = request.form.get('billing_interval', plan.billing_interval).strip()
        interval_count = request.form.get('interval_count', str(plan.interval_count)).strip()
        trial_days = request.form.get('trial_days', str(plan.trial_days)).strip()
        minimum_quantity = request.form.get('minimum_quantity', str(plan.minimum_quantity)).strip()
        start_date_raw = request.form.get('start_date', '').strip()
        end_date_raw = request.form.get('end_date', '').strip()
        renewal_setting = request.form.get('renewal_setting', plan.renewal_setting).strip()
        closure_setting = request.form.get('closure_setting', plan.closure_setting).strip()
        status = request.form.get('status', plan.status).strip()

        errors = []
        if not name:
            errors.append('Plan name is required.')
        if not code:
            errors.append('Plan code is required.')
        else:
            existing = SubscriptionPlan.query.filter_by(code=code).first()
            if existing and existing.id != plan.id:
                errors.append(f"A different plan with code '{code}' already exists.")

        try:
            price = Decimal(price_raw)
            if price < 0:
                errors.append('Price cannot be negative.')
        except (InvalidOperation, ValueError, TypeError):
            errors.append('Invalid price value.')
            price = plan.base_price

        try:
            min_qty = int(minimum_quantity)
            if min_qty < 1:
                errors.append('Minimum quantity must be at least 1.')
        except (ValueError, TypeError):
            errors.append('Invalid minimum quantity.')
            min_qty = plan.minimum_quantity

        try:
            trials = max(0, int(trial_days))
        except (ValueError, TypeError):
            trials = plan.trial_days

        try:
            int_count = max(1, int(interval_count))
        except (ValueError, TypeError):
            int_count = plan.interval_count

        start_date = plan.start_date
        if start_date_raw:
            try:
                start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
            except ValueError:
                errors.append('Invalid start date format.')

        end_date = None
        if end_date_raw:
            try:
                end_date = datetime.strptime(end_date_raw, '%Y-%m-%d').date()
                if end_date < start_date:
                    errors.append('End date cannot be prior to start date.')
            except ValueError:
                errors.append('Invalid end date format.')

        prod_id = int(product_id) if product_id and product_id.isdigit() else None

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'products/plan_form.html',
                plan=plan,
                products=products,
                intervals=SubscriptionPlan.INTERVALS,
                renewal_settings=SubscriptionPlan.RENEWAL_SETTINGS,
                closure_settings=SubscriptionPlan.CLOSURE_SETTINGS,
                statuses=SubscriptionPlan.STATUSES,
                form_data=request.form
            )

        plan.name = name
        plan.code = code
        plan.product_id = prod_id
        plan.description = description
        plan.base_price = price
        plan.billing_interval = billing_interval
        plan.interval_count = int_count
        plan.trial_days = trials
        plan.minimum_quantity = min_qty
        plan.start_date = start_date
        plan.end_date = end_date
        plan.renewal_setting = renewal_setting
        plan.closure_setting = closure_setting
        plan.status = status
        plan.is_active = (status == SubscriptionPlan.STATUS_ACTIVE)
        plan.updated_at = datetime.utcnow()

        db.session.commit()
        flash(f"Subscription plan '{plan.name}' updated successfully.", 'success')
        return redirect(url_for('products.plans_list'))

    return render_template(
        'products/plan_form.html',
        plan=plan,
        products=products,
        intervals=SubscriptionPlan.INTERVALS,
        renewal_settings=SubscriptionPlan.RENEWAL_SETTINGS,
        closure_settings=SubscriptionPlan.CLOSURE_SETTINGS,
        statuses=SubscriptionPlan.STATUSES,
        form_data={}
    )


@products_bp.route('/plans/<int:id>/toggle-status', methods=['POST'])
@login_required
@staff_required
def toggle_plan_status(id):
    """Enable or disable subscription plan."""
    plan = SubscriptionPlan.query.get_or_404(id)
    if plan.status == SubscriptionPlan.STATUS_ACTIVE:
        plan.status = SubscriptionPlan.STATUS_DISABLED
        plan.is_active = False
        flash(f"Plan '{plan.name}' disabled.", 'info')
    else:
        plan.status = SubscriptionPlan.STATUS_ACTIVE
        plan.is_active = True
        flash(f"Plan '{plan.name}' activated.", 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('products.plans_list'))


@products_bp.route('/plans/<int:id>/delete', methods=['POST'])
@login_required
@staff_required
def delete_plan(id):
    """Safely archive or delete subscription plan."""
    plan = SubscriptionPlan.query.get_or_404(id)
    if plan.subscriptions.count() > 0:
        plan.status = SubscriptionPlan.STATUS_ARCHIVED
        plan.is_active = False
        db.session.commit()
        flash(f"Plan '{plan.name}' has existing subscriptions and was archived instead of deleted.", 'warning')
        return redirect(url_for('products.plans_list'))

    plan_name = plan.name
    db.session.delete(plan)
    db.session.commit()
    flash(f"Plan '{plan_name}' deleted.", 'success')
    return redirect(url_for('products.plans_list'))


# ==============================================================================
# 4. JSON REST INTEGRATION APIs (for Sridhya & Fairooz)
# ==============================================================================

@products_bp.route('/api/products')
def api_products():
    """
    Returns products and their variants for Sridhya's quotation and subscription builders.
    Supports query param ?status=active (default) or ?type=subscription.
    """
    status = request.args.get('status', 'active')
    ptype = request.args.get('type')

    query = Product.query
    if status != 'all':
        query = query.filter_by(status=status)
    if ptype:
        query = query.filter_by(product_type=ptype)

    products = query.order_by(Product.name).all()
    return jsonify({
        'status': 'success',
        'count': len(products),
        'products': [p.to_dict(include_variants=True) for p in products]
    })


@products_bp.route('/api/products/<int:id>')
def api_product_detail(id):
    """Get single product details with nested variants."""
    product = Product.query.get_or_404(id)
    return jsonify({
        'status': 'success',
        'product': product.to_dict(include_variants=True)
    })


@products_bp.route('/api/products/<int:id>/calculate-price')
def api_calculate_price(id):
    """
    Calculate final price using base price and selected variant price.
    Formula: Base Sales Price + Additional Variant Price.
    Example: ₹2,000 + ₹560 = ₹2,560.
    """
    product = Product.query.get_or_404(id)
    variant_id = request.args.get('variant_id')

    variant = None
    if variant_id:
        try:
            variant = ProductVariant.query.filter_by(id=int(variant_id), product_id=product.id).first()
        except (ValueError, TypeError):
            variant = None

    base_price = float(product.base_price or 0.0)
    additional_price = float(variant.additional_price or variant.price or 0.0) if variant else 0.0
    final_price = round(base_price + additional_price, 2)

    return jsonify({
        'status': 'success',
        'product_id': product.id,
        'product_name': product.name,
        'base_price': base_price,
        'variant_id': variant.id if variant else None,
        'variant_name': variant.name if variant else None,
        'additional_price': additional_price,
        'final_price': final_price
    })


@products_bp.route('/api/plans')
def api_plans():
    """
    Returns subscription plans for Sridhya's quotation and subscription builders.
    Supports query params: ?interval=monthly|yearly|daily|weekly and ?status=active.
    """
    status = request.args.get('status', 'active')
    interval = request.args.get('interval')

    query = SubscriptionPlan.query
    if status != 'all':
        query = query.filter_by(status=status)
    if interval:
        query = query.filter_by(billing_interval=interval)

    plans = query.order_by(SubscriptionPlan.base_price.asc()).all()
    return jsonify({
        'status': 'success',
        'count': len(plans),
        'plans': [p.to_dict() for p in plans]
    })


@products_bp.route('/api/plans/<int:id>')
def api_plan_detail(id):
    """Get single subscription plan details."""
    plan = SubscriptionPlan.query.get_or_404(id)
    return jsonify({
        'status': 'success',
        'plan': plan.to_dict()
    })


@products_bp.route('/api/plans/<int:id>/validate', methods=['POST'])
def api_validate_plan(id):
    """
    Validate plan availability and minimum quantity for Sridhya's subscription orders.
    Accepts JSON body: {"quantity": 2, "date": "2026-10-31"}.
    """
    plan = SubscriptionPlan.query.get_or_404(id)
    payload = request.get_json(silent=True) or {}

    quantity = payload.get('quantity', 1)
    target_date = payload.get('date', None)

    is_valid, errors = plan.validate_subscription(quantity=quantity, target_date=target_date)

    return jsonify({
        'status': 'success' if is_valid else 'invalid',
        'valid': is_valid,
        'plan_id': plan.id,
        'plan_name': plan.name,
        'minimum_quantity': plan.minimum_quantity,
        'requested_quantity': quantity,
        'errors': errors
    }), (200 if is_valid else 400)


@products_bp.route('/api/discountable')
def api_discountable_products():
    """
    Returns active products with pricing for Fairooz's discount rule configuration.
    """
    products = Product.query.filter_by(status=Product.STATUS_ACTIVE).order_by(Product.name).all()
    return jsonify({
        'status': 'success',
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'sales_price': float(p.base_price or 0.0),
                'cost_price': float(p.cost_price or 0.0),
                'product_type': p.product_type
            }
            for p in products
        ]
    })


@products_bp.route('/api/products/<int:id>/pricing')
def api_product_pricing(id):
    """
    Returns sales price, cost price, and gross margin for Fairooz's discount limit checks.
    """
    product = Product.query.get_or_404(id)
    return jsonify({
        'status': 'success',
        'product_id': product.id,
        'name': product.name,
        'code': product.code,
        'sales_price': float(product.base_price or 0.0),
        'cost_price': float(product.cost_price or 0.0),
        'gross_margin': product.gross_margin,
        'margin_percentage': product.margin_percentage
    })

