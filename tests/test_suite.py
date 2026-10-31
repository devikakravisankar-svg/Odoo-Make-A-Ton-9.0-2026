from datetime import date
from app.extensions import db
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.models.plan import SubscriptionPlan
from app.models.quotation import Quotation
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine
from app.models.tax import Tax
from app.models.discount import Discount
from app.models.payment import Payment
from app.utils.validators import validate_password_strength
from app.utils.email_service import generate_reset_token, verify_reset_token

# ==========================================
# 1. PASSWORD VALIDATION TESTS
# ==========================================

def test_password_length_validation():
    # Exactly 8 characters (Must fail since requirement is MORE than 8 characters)
    is_valid, msg = validate_password_strength("Abc!1234")
    assert is_valid is False
    assert "more than 8" in msg

    # Less than 8 characters
    is_valid, msg = validate_password_strength("Abc!1")
    assert is_valid is False
    assert "more than 8" in msg

    # 9 characters with upper, lower, special
    is_valid, msg = validate_password_strength("Abc!12345")
    assert is_valid is True


def test_password_uppercase_validation():
    is_valid, msg = validate_password_strength("abcdef!123")
    assert is_valid is False
    assert "uppercase" in msg


def test_password_lowercase_validation():
    is_valid, msg = validate_password_strength("ABCDEF!123")
    assert is_valid is False
    assert "lowercase" in msg


def test_password_special_char_validation():
    is_valid, msg = validate_password_strength("Abcdef1234")
    assert is_valid is False
    assert "special character" in msg


def test_password_valid():
    is_valid, msg = validate_password_strength("StrongPass@2026")
    assert is_valid is True
    assert msg == ""


# ==========================================
# 2. AUTHENTICATION & TOKEN TESTS
# ==========================================

def test_customer_registration_success(client, app):
    response = client.post('/register', data={
        'full_name': 'New Customer',
        'username': 'newcustomer',
        'email': 'newcustomer@test.com',
        'phone': '1234567890',
        'password': 'SecurePassword@2026',
        'confirm_password': 'SecurePassword@2026'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='newcustomer').first()
        assert user is not None
        assert user.role == User.ROLE_CUSTOMER
        assert user.check_password('SecurePassword@2026')


def test_customer_registration_password_mismatch(client, app):
    response = client.post('/register', data={
        'full_name': 'Mismatch User',
        'username': 'mismatch',
        'email': 'mismatch@test.com',
        'password': 'SecurePassword@2026',
        'confirm_password': 'DifferentPassword@2026'
    }, follow_redirects=True)

    assert b"Passwords do not match" in response.data
    with app.app_context():
        assert User.query.filter_by(username='mismatch').first() is None


def test_customer_registration_weak_password(client, app):
    response = client.post('/register', data={
        'full_name': 'Weak User',
        'username': 'weakuser',
        'email': 'weak@test.com',
        'password': 'weak',
        'confirm_password': 'weak'
    }, follow_redirects=True)

    assert b"more than 8 characters" in response.data


def test_user_login_and_logout(client, customer_user):
    response = client.post('/login', data={
        'login_id': 'customer_test',
        'password': 'Cust@Test2026!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Customer Portal" in response.data

    logout_res = client.get('/logout', follow_redirects=True)
    assert b"You have been signed out" in logout_res.data


def test_user_login_invalid_password(client, customer_user):
    response = client.post('/login', data={
        'login_id': 'customer_test',
        'password': 'WrongPassword@123'
    }, follow_redirects=True)

    assert b"Invalid credentials" in response.data


def test_password_reset_token_workflow(client, app, customer_user):
    with app.app_context():
        user = User.query.filter_by(username='customer_test').first()
        token = generate_reset_token(user.id)
        verified_id = verify_reset_token(token)
        assert verified_id == user.id
        assert verify_reset_token("invalid-garbage-token") is None

    res = client.post(f'/reset-password/{token}', data={
        'password': 'BrandNewPass@2026',
        'confirm_password': 'BrandNewPass@2026'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Your password has been successfully reset" in res.data

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.check_password('BrandNewPass@2026')


# ==========================================
# 3. DATABASE MODELS & RELATIONSHIPS
# ==========================================

def test_models_and_relationships(app):
    with app.app_context():
        admin = User(username='admin_m', email='admin_m@test.com', full_name='Admin M', role=User.ROLE_ADMIN)
        admin.set_password('Admin@Test2026!')
        cust = User(username='cust_m', email='cust_m@test.com', full_name='Cust M', role=User.ROLE_CUSTOMER)
        cust.set_password('Cust@Test2026!')
        db.session.add_all([admin, cust])
        db.session.flush()

        prod = Product(name='ERP Module', code='ERP-MOD', base_price=100.00)
        db.session.add(prod)
        db.session.flush()

        variant = ProductVariant(product_id=prod.id, name='10 Seats', sku='ERP-MOD-10S', price=100.00)
        db.session.add(variant)

        plan = SubscriptionPlan(name='Gold Plan', code='GOLD-PLAN', base_price=99.00, billing_interval=SubscriptionPlan.INTERVAL_MONTHLY)
        db.session.add(plan)
        db.session.flush()

        quot = Quotation(quotation_number='QUOT-001', customer_id=cust.id, total_amount=99.00)
        db.session.add(quot)

        sub = Subscription(subscription_number='SUB-001', customer_id=cust.id, plan_id=plan.id, total_amount=99.00, start_date=date.today())
        db.session.add(sub)
        db.session.flush()

        inv = Invoice(invoice_number='INV-001', customer_id=cust.id, subscription_id=sub.id, due_date=date.today(), total_amount=99.00)
        db.session.add(inv)
        db.session.flush()

        line = InvoiceLine(invoice_id=inv.id, product_id=prod.id, description='Monthly Gold Plan', quantity=1, unit_price=99.00, line_total=99.00)
        db.session.add(line)

        tax = Tax(name='GST 18%', rate_percentage=18.00)
        db.session.add(tax)

        disc = Discount(code='FESTIVE10', discount_type=Discount.TYPE_PERCENTAGE, value=10.00, created_by=admin.id)
        db.session.add(disc)

        pay = Payment(payment_reference='PAY-TXN-001', invoice_id=inv.id, customer_id=cust.id, amount=99.00, status=Payment.STATUS_SUCCESSFUL)
        db.session.add(pay)

        db.session.commit()

        assert prod.variants.count() == 1
        assert cust.subscriptions.count() == 1
        assert cust.invoices.count() == 1
        assert inv.lines.count() == 1
        assert inv.payments.count() == 1
        assert disc.creator.id == admin.id
        assert disc.is_valid_now is True


# ==========================================
# 4. USER ROLES, PERMISSIONS & WORKFLOWS
# ==========================================

def test_unauthenticated_redirects_to_login(client):
    res = client.get('/dashboard/')
    assert res.status_code == 302
    assert '/login' in res.location


def test_customer_cannot_access_dashboard(client, customer_user):
    client.post('/login', data={'login_id': 'customer_test', 'password': 'Cust@Test2026!'})
    res = client.get('/dashboard/')
    assert res.status_code == 403


def test_staff_can_access_dashboard(client, staff_user):
    client.post('/login', data={'login_id': 'staff_test', 'password': 'Staff@Test2026!'})
    res = client.get('/dashboard/')
    assert res.status_code == 200
    assert b"Executive Dashboard" in res.data


def test_staff_cannot_create_staff_accounts(client, staff_user):
    client.post('/login', data={'login_id': 'staff_test', 'password': 'Staff@Test2026!'})
    res = client.get('/dashboard/staff/new')
    assert res.status_code == 403


def test_admin_can_create_staff_accounts(client, app, admin_user):
    client.post('/login', data={'login_id': 'admin_test', 'password': 'Admin@Test2026!'})
    res = client.get('/dashboard/staff/new')
    assert res.status_code == 200

    create_res = client.post('/dashboard/staff/new', data={
        'full_name': 'New Staff Officer',
        'username': 'officer1',
        'email': 'officer1@odoo.local',
        'password': 'StaffPass@2026'
    }, follow_redirects=True)

    assert create_res.status_code == 200
    assert b"successfully created" in create_res.data

    with app.app_context():
        created = User.query.filter_by(username='officer1').first()
        assert created is not None
        assert created.role == User.ROLE_STAFF


def test_customer_invoice_isolation(client, app):
    with app.app_context():
        cust1 = User(username='c1', email='c1@test.com', full_name='C1', role=User.ROLE_CUSTOMER)
        cust1.set_password('Pass@12345')

        cust2 = User(username='c2', email='c2@test.com', full_name='C2', role=User.ROLE_CUSTOMER)
        cust2.set_password('Pass@12345')

        db.session.add_all([cust1, cust2])
        db.session.flush()

        inv2 = Invoice(
            invoice_number='INV-C2-001',
            customer_id=cust2.id,
            issue_date=date.today(),
            due_date=date.today(),
            status=Invoice.STATUS_PENDING,
            total_amount=150.00
        )
        db.session.add(inv2)
        db.session.commit()
        inv2_id = inv2.id

    client.post('/login', data={'login_id': 'c1', 'password': 'Pass@12345'})
    res = client.get(f'/portal/invoices/{inv2_id}')
    assert res.status_code == 403


def test_staff_cannot_manage_discount_rules(client, staff_user):
    client.post('/login', data={'login_id': 'staff_test', 'password': 'Staff@Test2026!'})
    assert client.get('/dashboard/discounts').status_code == 403
    assert client.get('/dashboard/discounts/new').status_code == 403
    assert client.post('/dashboard/discounts/new', data={'code': 'NO', 'value': 10}).status_code == 403


def test_admin_can_manage_discount_rules(client, app, admin_user):
    client.post('/login', data={'login_id': 'admin_test', 'password': 'Admin@Test2026!'})
    assert client.get('/dashboard/discounts').status_code == 200

    create_res = client.post('/dashboard/discounts/new', data={
        'code': 'SPECIAL20',
        'discount_type': 'percentage',
        'value': '20.00',
        'min_purchase_amount': '50.00'
    }, follow_redirects=True)
    assert create_res.status_code == 200

    with app.app_context():
        disc = Discount.query.filter_by(code='SPECIAL20').first()
        assert disc is not None
        disc_id = disc.id

    toggle_res = client.post(f'/dashboard/discounts/{disc_id}/toggle', follow_redirects=True)
    assert toggle_res.status_code == 200
    with app.app_context():
        assert db.session.get(Discount, disc_id).is_active is False


def test_customer_portal_subscribe_and_pay_flow(client, app, customer_user):
    with app.app_context():
        plan = SubscriptionPlan(name='Standard Cloud', code='PLAN-STD-TEST', base_price=100.00, billing_interval=SubscriptionPlan.INTERVAL_MONTHLY)
        db.session.add(plan)
        db.session.commit()
        plan_id = plan.id

    client.post('/login', data={'login_id': 'customer_test', 'password': 'Cust@Test2026!'})

    sub_res = client.post(f'/portal/subscribe/{plan_id}', follow_redirects=True)
    assert sub_res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username='customer_test').first()
        inv = user.invoices.first()
        inv_id = inv.id

    pay_res = client.post(f'/portal/invoices/{inv_id}/pay', data={'payment_method': 'card'}, follow_redirects=True)
    assert pay_res.status_code == 200

    with app.app_context():
        inv_after = db.session.get(Invoice, inv_id)
        assert inv_after.status == Invoice.STATUS_PAID
        payment = Payment.query.filter_by(invoice_id=inv_id).first()
        paid_amount = float(payment.amount)

    client.get('/logout')
    with app.app_context():
        admin = User(username='dash_admin', email='dash@test.local', full_name='Dash Admin', role=User.ROLE_ADMIN)
        admin.set_password('Admin@Test2026!')
        db.session.add(admin)
        db.session.commit()

    client.post('/login', data={'login_id': 'dash_admin', 'password': 'Admin@Test2026!'})
    dash_res = client.get('/dashboard/')
    assert dash_res.status_code == 200
    expected_revenue = f"${paid_amount:.2f}".encode('utf-8')
    assert expected_revenue in dash_res.data
