from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.models.plan import SubscriptionPlan
from app.models.invoice import Invoice, InvoiceLine


# ==============================================================================
# 1. PRODUCT MODEL & MARGIN CALCULATIONS
# ==============================================================================

def test_product_creation_and_margins(app):
    with app.app_context():
        prod = Product(
            name="Cloud Storage Pro",
            code="CLOUD-PRO",
            product_type=Product.TYPE_SERVICE,
            base_price=2000.00,
            cost_price=1200.00,
            notes="Requires AWS S3 bucket allocation",
            status=Product.STATUS_ACTIVE
        )
        db.session.add(prod)
        db.session.commit()

        assert prod.id is not None
        assert prod.sales_price == Decimal('2000.00')
        assert prod.cost_price == Decimal('1200.00')
        assert prod.gross_margin == 800.00
        assert prod.margin_percentage == 40.0
        assert prod.is_active is True
        assert "CLOUD-PRO" in repr(prod)

        d = prod.to_dict()
        assert d['name'] == "Cloud Storage Pro"
        assert d['gross_margin'] == 800.00


# ==============================================================================
# 2. PRODUCT VARIANTS & FINAL PRICE FORMULA (Base + Variant)
# ==============================================================================

def test_variant_final_price_calculation(app):
    """
    Verify exact requirement:
    Base price ?2,000 + Additional variant price ?560 = Final price ?2,560.
    """
    with app.app_context():
        prod = Product(
            name="Accounting Suite",
            code="ACCT-BASE",
            base_price=2000.00,
            cost_price=1000.00
        )
        db.session.add(prod)
        db.session.flush()

        variant = ProductVariant(
            product_id=prod.id,
            name="Accounting Suite: Enterprise Edition",
            variant_name="Edition",
            variant_value="Enterprise",
            sku="ACCT-ENT",
            additional_price=560.00
        )
        db.session.add(variant)
        db.session.commit()

        # Check variant-side calculation
        assert variant.calculate_final_price() == 2560.00

        # Check product-side calculation
        assert prod.calculate_price(variant.id) == 2560.00

        # Calling without variant returns base price
        assert prod.calculate_price() == 2000.00

        # Serialization checks
        v_dict = variant.to_dict(include_product=True)
        assert v_dict['final_price'] == 2560.00
        assert v_dict['additional_price'] == 560.00
        assert v_dict['product_name'] == "Accounting Suite"


# ==============================================================================
# 3. SUBSCRIPTION PLAN CYCLES, AVAILABILITY & QUANTITY VALIDATION
# ==============================================================================

def test_subscription_plan_intervals_and_validation(app):
    with app.app_context():
        today = date.today()

        # Test daily plan
        daily_plan = SubscriptionPlan(
            name="Daily Micro Cloud",
            code="PLAN-DAILY",
            billing_interval=SubscriptionPlan.INTERVAL_DAILY,
            base_price=15.00,
            minimum_quantity=1,
            start_date=today,
            status=SubscriptionPlan.STATUS_ACTIVE
        )

        # Test yearly plan with date window and minimum quantity of 5
        yearly_plan = SubscriptionPlan(
            name="Corporate Annual",
            code="PLAN-CORP-YR",
            billing_interval=SubscriptionPlan.INTERVAL_YEARLY,
            base_price=4900.00,
            minimum_quantity=5,
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=30),
            renewal_setting=SubscriptionPlan.RENEWAL_AUTOMATIC,
            closure_setting=SubscriptionPlan.CLOSURE_PERIOD_END,
            status=SubscriptionPlan.STATUS_ACTIVE
        )

        # Test expired plan
        expired_plan = SubscriptionPlan(
            name="Flash Sale Plan",
            code="PLAN-FLASH",
            billing_interval=SubscriptionPlan.INTERVAL_MONTHLY,
            base_price=99.00,
            minimum_quantity=1,
            start_date=today - timedelta(days=60),
            end_date=today - timedelta(days=5),
            status=SubscriptionPlan.STATUS_ACTIVE
        )

        db.session.add_all([daily_plan, yearly_plan, expired_plan])
        db.session.commit()

        # Availability checks
        assert daily_plan.is_currently_available() is True
        assert yearly_plan.is_currently_available() is True
        assert expired_plan.is_currently_available() is False

        # Quantity validation on yearly plan (min 5)
        valid, errs = yearly_plan.validate_subscription(quantity=5)
        assert valid is True
        assert len(errs) == 0

        valid_fail, errs_fail = yearly_plan.validate_subscription(quantity=2)
        assert valid_fail is False
        assert "Minimum quantity required" in errs_fail[0]

        # Order on expired plan
        exp_valid, exp_errs = expired_plan.validate_subscription(quantity=1)
        assert exp_valid is False
        assert "not currently available" in exp_errs[0]


# ==============================================================================
# 4. WEB CRUD FOR PRODUCTS & VARIANTS
# ==============================================================================

def test_products_web_crud_and_search(client, app, staff_user):
    # Log in as staff
    client.post('/login', data={'login_id': 'staff_test', 'password': 'Staff@Test2026!'})

    # 1. Create Product
    res = client.post('/products/create', data={
        'name': 'CRM Automation Pack',
        'code': 'CRM-AUTO',
        'product_type': 'service',
        'sales_price': '1500.00',
        'cost_price': '900.00',
        'description': 'Automated lead pipelines and scoring.',
        'notes': 'Staff setup required in 24 hours.',
        'status': 'active'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"CRM Automation Pack" in res.data

    with app.app_context():
        p = Product.query.filter_by(code='CRM-AUTO').first()
        assert p is not None
        p_id = p.id

    # 2. View details
    res = client.get(f'/products/{p_id}')
    assert res.status_code == 200
    assert b"CRM Automation Pack" in res.data
    assert b"CRM-AUTO" in res.data

    # 3. Add variant
    res = client.post(f'/products/{p_id}/variants/create', data={
        'variant_name': 'Team Size',
        'variant_value': '10 Users',
        'sku': 'CRM-AUTO-10U',
        'additional_price': '400.00'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Final Price" in res.data

    with app.app_context():
        p = db.session.get(Product, p_id)
        assert p.variants.count() == 1
        var = p.variants.first()
        assert var.calculate_final_price() == 1900.00

    # 4. Edit product
    res = client.post(f'/products/{p_id}/edit', data={
        'name': 'CRM Automation Pack Pro',
        'code': 'CRM-AUTO',
        'product_type': 'service',
        'sales_price': '1600.00',
        'cost_price': '900.00',
        'description': 'Updated description.',
        'notes': 'Updated notes.',
        'status': 'active'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        p = db.session.get(Product, p_id)
        assert p.name == 'CRM Automation Pack Pro'
        assert p.base_price == Decimal('1600.00')

    # 5. Search and filters
    res = client.get('/products/?q=CRM&type=service')
    assert res.status_code == 200
    assert b"CRM Automation Pack Pro" in res.data

    # 6. Toggle archive
    res = client.post(f'/products/{p_id}/toggle-status', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        p = db.session.get(Product, p_id)
        assert p.status == Product.STATUS_ARCHIVED
        assert p.is_active is False


# ==============================================================================
# 5. WEB CRUD FOR SUBSCRIPTION PLANS
# ==============================================================================

def test_subscription_plans_web_crud(client, app, staff_user):
    client.post('/login', data={'login_id': 'staff_test', 'password': 'Staff@Test2026!'})

    # Create plan
    res = client.post('/products/plans/create', data={
        'name': 'Weekly Developer Pass',
        'code': 'PLAN-DEV-WK',
        'price': '250.00',
        'billing_interval': 'weekly',
        'interval_count': '1',
        'trial_days': '7',
        'minimum_quantity': '2',
        'start_date': date.today().strftime('%Y-%m-%d'),
        'renewal_setting': 'automatic',
        'closure_setting': 'at-period-end',
        'status': 'active',
        'description': 'Weekly access for independent developers.'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        plan = SubscriptionPlan.query.filter_by(code='PLAN-DEV-WK').first()
        assert plan is not None
        assert plan.base_price == Decimal('250.00')
        assert plan.billing_interval == 'weekly'
        assert plan.minimum_quantity == 2
        plan_id = plan.id

    # View plan detail
    res = client.get(f'/products/plans/{plan_id}')
    assert res.status_code == 200
    assert b"Weekly Developer Pass" in res.data

    # Toggle disable
    res = client.post(f'/products/plans/{plan_id}/toggle-status', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        plan = db.session.get(SubscriptionPlan, plan_id)
        assert plan.status == SubscriptionPlan.STATUS_DISABLED
        assert plan.is_active is False


# ==============================================================================
# 6. INTEGRATION REST APIs (Sridhya & Fairooz)
# ==============================================================================

def test_integration_apis(client, app):
    with app.app_context():
        prod = Product(
            name="HR Management Core",
            code="HR-CORE",
            base_price=3000.00,
            cost_price=1800.00,
            status=Product.STATUS_ACTIVE
        )
        db.session.add(prod)
        db.session.flush()

        v = ProductVariant(
            product_id=prod.id,
            name="HR Core - 50 Employees",
            sku="HR-CORE-50E",
            additional_price=800.00
        )
        db.session.add(v)

        plan = SubscriptionPlan(
            name="HR Monthly",
            code="PLAN-HR-M",
            product_id=prod.id,
            base_price=3000.00,
            billing_interval='monthly',
            minimum_quantity=3,
            start_date=date.today(),
            status='active'
        )
        db.session.add(plan)
        db.session.commit()
        prod_id = prod.id
        var_id = v.id
        plan_id = plan.id

    # 1. GET /products/api/products
    res = client.get('/products/api/products')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert any(p['code'] == 'HR-CORE' for p in data['products'])

    # 2. Dynamic price calculation: Base ?3000 + Variant ?800 = Final ?3800
    res = client.get(f'/products/api/products/{prod_id}/calculate-price?variant_id={var_id}')
    assert res.status_code == 200
    calc_data = res.get_json()
    assert calc_data['base_price'] == 3000.00
    assert calc_data['additional_price'] == 800.00
    assert calc_data['final_price'] == 3800.00

    # 3. GET /products/api/plans
    res = client.get('/products/api/plans?interval=monthly')
    assert res.status_code == 200
    plan_data = res.get_json()
    assert plan_data['status'] == 'success'
    assert any(p['code'] == 'PLAN-HR-M' for p in plan_data['plans'])

    # 4. POST /products/api/plans/<id>/validate (minimum quantity check)
    # Valid quantity (3 >= 3)
    res = client.post(f'/products/api/plans/{plan_id}/validate', json={'quantity': 3})
    assert res.status_code == 200
    assert res.get_json()['valid'] is True

    # Invalid quantity (1 < 3)
    res = client.post(f'/products/api/plans/{plan_id}/validate', json={'quantity': 1})
    assert res.status_code == 400
    assert res.get_json()['valid'] is False
    assert len(res.get_json()['errors']) > 0

    # 5. GET /products/api/discountable (for Fairooz)
    res = client.get('/products/api/discountable')
    assert res.status_code == 200
    assert any(p['code'] == 'HR-CORE' for p in res.get_json()['products'])

    # 6. GET /products/api/products/<id>/pricing (for Fairooz margin ceiling)
    res = client.get(f'/products/api/products/{prod_id}/pricing')
    assert res.status_code == 200
    pricing = res.get_json()
    assert pricing['sales_price'] == 3000.00
    assert pricing['cost_price'] == 1800.00
    assert pricing['gross_margin'] == 1200.00
    assert pricing['margin_percentage'] == 40.0


# ==============================================================================
# 7. ACCESS CONTROL SECURITY
# ==============================================================================

def test_access_control(client, customer_user):
    # Unauthenticated user redirected to login
    res = client.get('/products/')
    assert res.status_code == 302
    assert '/login' in res.location

    # Customer user denied access (403 Forbidden)
    client.post('/login', data={'login_id': 'customer_test', 'password': 'Cust@Test2026!'})
    res = client.get('/products/')
    assert res.status_code == 403


# ==============================================================================
# 8. QUOTATIONS & SUBSCRIPTIONS INTEGRATION CONNECTIONS
# ==============================================================================

def test_quotation_line_calculation(app):
    with app.app_context():
        prod = Product(name="Enterprise Server", code="SRV-ENT", base_price=2000.00, cost_price=1200.00)
        db.session.add(prod)
        db.session.flush()

        variant = ProductVariant(
            product_id=prod.id,
            name="1TB NVMe Storage",
            variant_name="Storage",
            variant_value="1TB",
            sku="SRV-1TB",
            additional_price=560.00
        )
        db.session.add(variant)
        db.session.commit()

        # 1 unit without variant: 2000 * 1 = 2000
        assert prod.calculate_line_total(quantity=1) == 2000.00

        # 3 units with variant: (2000 + 560) * 3 = 2560 * 3 = 7680
        assert prod.calculate_line_total(variant_id=variant.id, quantity=3) == 7680.00

        # Active variants picker helper
        active_vars = prod.get_active_variants()
        assert len(active_vars) == 1
        assert active_vars[0].sku == "SRV-1TB"


def test_next_billing_date_calculation(app):
    with app.app_context():
        ref_date = date(2026, 10, 31)

        daily = SubscriptionPlan(name="P-Daily", code="P-D", billing_interval="daily", base_price=10.00)
        weekly = SubscriptionPlan(name="P-Weekly", code="P-W", billing_interval="weekly", base_price=50.00)
        monthly = SubscriptionPlan(name="P-Monthly", code="P-M", billing_interval="monthly", base_price=200.00)
        yearly = SubscriptionPlan(name="P-Yearly", code="P-Y", billing_interval="yearly", base_price=2000.00)

        # Daily: 31 Oct + 1 day = 1 Nov 2026
        assert daily.calculate_next_billing_date(start_date=ref_date) == date(2026, 11, 1)

        # Weekly: 31 Oct + 7 days = 7 Nov 2026
        assert weekly.calculate_next_billing_date(start_date=ref_date) == date(2026, 11, 7)

        # Monthly: Next month (Nov 2026)
        next_m = monthly.calculate_next_billing_date(start_date=ref_date)
        assert next_m.month == 11
        assert next_m.year == 2026

        # Yearly: Next year (31 Oct 2027)
        assert yearly.calculate_next_billing_date(start_date=ref_date) == date(2027, 10, 31)


def test_quotation_and_subscription_bridge_apis(client, app):
    with app.app_context():
        prod = Product(name="POS Terminal", code="POS-TERM", base_price=2000.00, status=Product.STATUS_ACTIVE)
        db.session.add(prod)
        db.session.flush()

        v = ProductVariant(product_id=prod.id, name="Touch Display", sku="POS-TOUCH", additional_price=560.00)
        db.session.add(v)

        plan = SubscriptionPlan(
            name="POS Support Gold",
            code="POS-GOLD-M",
            base_price=500.00,
            billing_interval="monthly",
            minimum_quantity=2,
            start_date=date.today(),
            trial_days=14,
            status="active"
        )
        db.session.add(plan)
        db.session.commit()

        prod_id = prod.id
        var_id = v.id
        plan_id = plan.id

    # Test /api/quotations/calculate-line
    # 2 units * (2000 + 560) = 5120
    res = client.post('/products/api/quotations/calculate-line', json={
        'product_id': prod_id,
        'variant_id': var_id,
        'quantity': 2
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['unit_price'] == 2560.00
    assert data['line_total'] == 5120.00
    assert data['product_code'] == "POS-TERM"

    # Test /api/subscriptions/prepare (Valid)
    res = client.post('/products/api/subscriptions/prepare', json={
        'plan_id': plan_id,
        'quantity': 2,
        'start_date': date.today().strftime('%Y-%m-%d')
    })
    assert res.status_code == 200
    sub_data = res.get_json()
    assert sub_data['valid'] is True
    assert sub_data['order']['total_amount'] == 1000.00
    assert sub_data['order']['trial_days'] == 14

    # Test /api/subscriptions/prepare (Invalid quantity 1 < min 2)
    res_fail = client.post('/products/api/subscriptions/prepare', json={
        'plan_id': plan_id,
        'quantity': 1
    })
    assert res_fail.status_code == 400
    assert res_fail.get_json()['valid'] is False
