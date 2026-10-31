from datetime import date
from app.extensions import db
from app.models.user import User
from app.models.invoice import Invoice
from app.models.plan import SubscriptionPlan
from app.models.subscription import Subscription

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
    """Enforce permission rule: ONLY Admin can create staff accounts."""
    client.post('/login', data={'login_id': 'staff_test', 'password': 'Staff@Test2026!'})
    res = client.get('/dashboard/staff/new')
    assert res.status_code == 403


def test_admin_can_create_staff_accounts(client, app, admin_user):
    """Admin has full privileges to create staff."""
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
    """Backend route protection: Customer can only access their own invoices."""
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

    # Log in as cust1 and try to access cust2's invoice
    client.post('/login', data={'login_id': 'c1', 'password': 'Pass@12345'})
    res = client.get(f'/portal/invoices/{inv2_id}')
    assert res.status_code == 403
