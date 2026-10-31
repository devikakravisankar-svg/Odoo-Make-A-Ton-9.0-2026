import os
from flask import Flask, redirect, url_for
from flask_login import current_user
from app.config import config_by_name
from app.extensions import db, login_manager

def create_app(config_name: str = None) -> Flask:
    """
    Application Factory for Odoo Make-A-Ton Subscription Management System.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.portal import portal_bp
    from app.blueprints.products import products_bp
    from app.blueprints.subscriptions import subscriptions_bp
    from app.blueprints.billing import billing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(subscriptions_bp)
    app.register_blueprint(billing_bp)

    # Landing page routing
    @app.route('/')
    def root():
        if current_user.is_authenticated:
            if current_user.is_admin_or_staff:
                return redirect(url_for('dashboard.index'))
            return redirect(url_for('portal.index'))
        return redirect(url_for('auth.login'))

    # Register CLI management commands
    register_commands(app)

    return app


def register_commands(app: Flask):
    """Register custom Flask CLI management commands."""
    import click

    @app.cli.command("init-db")
    def init_db():
        """Creates all database tables in MySQL."""
        with app.app_context():
            db.create_all()
            click.echo("Database tables created successfully in MySQL.")

    @app.cli.command("seed-admin")
    @click.option('--email', default=None, help='Admin email address')
    @click.option('--username', default=None, help='Admin username')
    @click.option('--password', default=None, help='Admin password')
    def seed_admin(email, username, password):
        """Seed the initial administrator account."""
        from app.models.user import User

        with app.app_context():
            admin_email = email or os.getenv('INITIAL_ADMIN_EMAIL', 'admin@odoo.local')
            admin_username = username or os.getenv('INITIAL_ADMIN_USERNAME', 'admin')
            admin_password = password or os.getenv('INITIAL_ADMIN_PASSWORD', 'Admin@Odoo2026!')

            existing = User.query.filter(
                (User.email == admin_email) | (User.username == admin_username)
            ).first()

            if existing:
                click.echo(f"Admin user already exists: {existing.username} ({existing.email})")
                return

            admin = User(
                username=admin_username,
                email=admin_email,
                full_name="System Administrator",
                role=User.ROLE_ADMIN,
                is_active=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            click.echo(f"Admin account created successfully: {admin_username} / {admin_email}")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Seeds initial demo products, plans, and taxes for testing."""
        from datetime import date, timedelta
        from app.models.user import User
        from app.models.product import Product, ProductVariant
        from app.models.plan import SubscriptionPlan
        from app.models.tax import Tax

        with app.app_context():
            # Seed standard taxes
            if not Tax.query.first():
                gst = Tax(name="Standard GST", rate_percentage=18.00, description="18% Goods & Services Tax")
                vat = Tax(name="Standard VAT", rate_percentage=5.00, description="5% Value Added Tax")
                db.session.add_all([gst, vat])

            # Seed demo products
            if not Product.query.first():
                p1 = Product(name="Odoo Cloud ERP Core", code="ERP-CORE", description="Enterprise Resource Planning Core Suite", base_price=49.00)
                p2 = Product(name="Odoo CRM & Sales Pro", code="CRM-PRO", description="Customer Relationship Management & Sales Pipelines", base_price=29.00)
                db.session.add_all([p1, p2])
                db.session.flush()

                # Add variants
                v1 = ProductVariant(product_id=p1.id, name="Cloud ERP - 5 Users", sku="ERP-CORE-5U", price=49.00, attributes={"users": 5, "storage": "50GB"})
                v2 = ProductVariant(product_id=p1.id, name="Cloud ERP - 20 Users", sku="ERP-CORE-20U", price=149.00, attributes={"users": 20, "storage": "200GB"})
                db.session.add_all([v1, v2])

            # Seed demo plans
            if not SubscriptionPlan.query.first():
                plan_monthly = SubscriptionPlan(
                    name="Business Standard - Monthly",
                    code="PLAN-STD-MONTHLY",
                    description="Full suite access billed monthly",
                    billing_interval=SubscriptionPlan.INTERVAL_MONTHLY,
                    interval_count=1,
                    base_price=49.00,
                    trial_days=14
                )
                plan_yearly = SubscriptionPlan(
                    name="Business Enterprise - Yearly",
                    code="PLAN-ENT-YEARLY",
                    description="Full suite access with priority support billed annually",
                    billing_interval=SubscriptionPlan.INTERVAL_YEARLY,
                    interval_count=1,
                    base_price=490.00,
                    trial_days=30
                )
                db.session.add_all([plan_monthly, plan_yearly])

            db.session.commit()
            click.echo("Demo data (taxes, products, plans) seeded successfully.")

    @app.cli.command("check-db")
    def check_db():
        """Verifies MySQL database connectivity and PyMySQL driver configuration."""
        from sqlalchemy import text
        from urllib.parse import urlparse

        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        # Redact password in logs for security
        safe_uri = db_uri
        if '@' in db_uri and ':' in db_uri:
            prefix = db_uri.split('@')[0]
            scheme_and_user = prefix.split(':')[0] + ':' + prefix.split(':')[1] if len(prefix.split(':')) > 1 else prefix
            safe_uri = f"{scheme_and_user}:****@{db_uri.split('@')[1]}"

        click.echo(f"Configured Database URI: {safe_uri}")

        try:
            with app.app_context():
                with db.engine.connect() as connection:
                    result = connection.execute(text("SELECT 1")).scalar()
                    click.echo("Connection test succeeded: SELECT 1 returned successfully.")
                    click.echo("MySQL + SQLAlchemy + PyMySQL driver is healthy and functioning properly!")
        except Exception as e:
            click.echo(f"\n[ERROR] Unable to connect to database: {e}")
            click.echo("Troubleshooting tips:")
            click.echo("1. Ensure your local MySQL server is started (e.g. via Windows Services, XAMPP, or Docker).")
            click.echo("2. Verify your credentials in .env (MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DB).")
            click.echo("3. Make sure the target database exists in MySQL: CREATE DATABASE subscription_management_db;\n")
