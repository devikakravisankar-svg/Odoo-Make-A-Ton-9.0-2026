from app.extensions import db
from app.models.user import User
from app.utils.email_service import generate_reset_token, verify_reset_token

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
    # Success login
    response = client.post('/login', data={
        'login_id': 'customer_test',
        'password': 'Cust@Test2026!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Customer Portal" in response.data

    # Logout
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

        # Test invalid token
        assert verify_reset_token("invalid-garbage-token") is None

    # Test reset password route with token
    res = client.post(f'/reset-password/{token}', data={
        'password': 'BrandNewPass@2026',
        'confirm_password': 'BrandNewPass@2026'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Your password has been successfully reset" in res.data

    with app.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed.check_password('BrandNewPass@2026')
