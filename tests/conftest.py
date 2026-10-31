import pytest
from app import create_app
from app.extensions import db
from app.models.user import User

@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for each test."""
    application = create_app('testing')

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the application."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Creates a persistent Admin user."""
    with app.app_context():
        user = User(
            username='admin_test',
            email='admin@test.local',
            full_name='Admin Tester',
            role=User.ROLE_ADMIN,
            is_active=True
        )
        user.set_password('Admin@Test2026!')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def staff_user(app):
    """Creates a persistent Staff user."""
    with app.app_context():
        user = User(
            username='staff_test',
            email='staff@test.local',
            full_name='Staff Tester',
            role=User.ROLE_STAFF,
            is_active=True
        )
        user.set_password('Staff@Test2026!')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def customer_user(app):
    """Creates a persistent Customer user."""
    with app.app_context():
        user = User(
            username='customer_test',
            email='customer@test.local',
            full_name='Customer Tester',
            role=User.ROLE_CUSTOMER,
            is_active=True
        )
        user.set_password('Cust@Test2026!')
        db.session.add(user)
        db.session.commit()
        return user
