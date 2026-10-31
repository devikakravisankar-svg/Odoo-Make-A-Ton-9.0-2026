import os
import pymysql
from datetime import date, timedelta
from decimal import Decimal
from config import Config

def ensure_database_exists():
    """Ensures MySQL database exists before initializing tables."""
    try:
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            port=int(Config.MYSQL_PORT)
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        conn.close()
        print(f"[OK] MySQL Database '{Config.MYSQL_DB}' confirmed.")
    except Exception as e:
        print(f"[!] Warning: Could not auto-create database (may already exist or MySQL not running): {e}")

def seed():
    ensure_database_exists()

    from app import create_app
    from extensions import db
    from models.user import User
    from models.product import Product, ProductVariant
    from models.plan import Plan
    from models.subscription import Subscription
    from models.invoice import Invoice
    from models.invoice_line import InvoiceLine
    from models.discount import Discount
    from models.payment import Payment
    from models.invoice_discount import InvoiceDiscount

    app = create_app()
    with app.app_context():
        # Drop and create tables for clean demo
        db.create_all()

        if User.query.filter_by(email='admin@brightloop.com').first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding Brightloop Subscription Management System data into MySQL...")

        # 1. Users
        admin = User(name='Sarah Jenkins (Admin)', email='admin@brightloop.com', role='admin')
        admin.set_password('Admin@1234')

        staff = User(name='Michael Scott (Staff)', email='staff@brightloop.com', role='staff')
        staff.set_password('Staff@1234')

        cust1 = User(name='Acme Global Corp', email='billing@acme.com', role='customer')
        cust1.set_password('Customer@1234')

        cust2 = User(name='Sunny Cafe & Bakery', email='finance@sunnycafe.com', role='customer')
        cust2.set_password('Customer@1234')

        cust3 = User(name='Apex Tech Logistics', email='accounts@apextech.io', role='customer')
        cust3.set_password('Customer@1234')

        db.session.add_all([admin, staff, cust1, cust2, cust3])
        db.session.commit()

        # 2. Products & Variants
        p_crm = Product(name='Brightloop Cloud ERP', product_type='software', sales_price=Decimal('150.00'), cost_price=Decimal('40.00'), notes='Main platform license')
        p_addon = Product(name='Recurring Invoicing Engine', product_type='add-on', sales_price=Decimal('50.00'), cost_price=Decimal('10.00'), notes='Automated billing module')
        p_support = Product(name='24/7 Dedicated Support', product_type='service', sales_price=Decimal('100.00'), cost_price=Decimal('30.00'), notes='Priority SLA support')

        db.session.add_all([p_crm, p_addon, p_support])
        db.session.commit()

        # Variant: Odoo Brand adds 560 to price
        var_odoo = ProductVariant(product_id=p_crm.id, variant_name='Odoo Certified Edition', price_extra=Decimal('560.00'))
        db.session.add(var_odoo)
        db.session.commit()

        # 3. Plans
        plan_monthly = Plan(name='Business Monthly', billing_interval='monthly', cost=Decimal('200.00'), min_quantity=1, auto_close=False, can_pause=True, can_renew=True)
        plan_annual = Plan(name='Enterprise Annual', billing_interval='yearly', cost=Decimal('2200.00'), min_quantity=1, auto_close=False, can_pause=True, can_renew=True)

        db.session.add_all([plan_monthly, plan_annual])
        db.session.commit()

        # 4. Subscriptions
        today = date.today()
        sub1 = Subscription(subscription_number='SUB-BRIGHT-001', customer_id=cust1.id, plan_id=plan_annual.id, start_date=today - timedelta(days=90), expiry_date=today + timedelta(days=275), payment_terms='Net 30', status='active')
        sub2 = Subscription(subscription_number='SUB-BRIGHT-002', customer_id=cust2.id, plan_id=plan_monthly.id, start_date=today - timedelta(days=45), expiry_date=today + timedelta(days=320), payment_terms='Immediate Payment', status='active')
        sub3 = Subscription(subscription_number='SUB-BRIGHT-003', customer_id=cust3.id, plan_id=plan_monthly.id, start_date=today - timedelta(days=10), expiry_date=today + timedelta(days=355), payment_terms='Net 15', status='active')

        db.session.add_all([sub1, sub2, sub3])
        db.session.commit()

        # 5. Discount Rules (Member 4)
        d_pct = Discount(
            name='Summer SaaS Promo 15% OFF',
            code='SUMMER15',
            discount_type='percentage',
            discount_value=Decimal('15.00'),
            min_purchase_amount=Decimal('100.00'),
            min_quantity=1,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=60),
            max_usage_limit=100,
            current_usage_count=4,
            scope='subscription',
            is_active=True
        )

        d_fixed = Discount(
            name='High-Volume Enterprise $50 OFF',
            code='ENTERPRISE50',
            discount_type='fixed',
            discount_value=Decimal('50.00'),
            min_purchase_amount=Decimal('250.00'),
            min_quantity=2,
            start_date=today - timedelta(days=15),
            end_date=today + timedelta(days=90),
            max_usage_limit=50,
            current_usage_count=2,
            scope='subscription',
            is_active=True
        )

        d_prod = Discount(
            name='ERP Module Loyalty $30 OFF',
            code='ERP30',
            discount_type='fixed',
            discount_value=Decimal('30.00'),
            min_purchase_amount=Decimal('50.00'),
            min_quantity=1,
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=45),
            max_usage_limit=25,
            current_usage_count=1,
            scope='product',
            applicable_product_id=p_crm.id,
            is_active=True
        )

        d_expired = Discount(
            name='Early Bird 2025 Discount (Expired)',
            code='EARLY2025',
            discount_type='percentage',
            discount_value=Decimal('25.00'),
            min_purchase_amount=Decimal('0.00'),
            min_quantity=0,
            start_date=today - timedelta(days=90),
            end_date=today - timedelta(days=10),
            max_usage_limit=10,
            current_usage_count=10,
            scope='subscription',
            is_active=False
        )

        db.session.add_all([d_pct, d_fixed, d_prod, d_expired])
        db.session.commit()

        # 6. Invoices
        # Invoice 1: Fully Paid ($2,200.00)
        inv1 = Invoice(
            invoice_number='INV-2026-001',
            subscription_id=sub1.id,
            customer_id=cust1.id,
            invoice_date=today - timedelta(days=60),
            due_date=today - timedelta(days=30),
            subtotal=Decimal('2200.00'),
            tax_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('2200.00'),
            status='paid',
            payment_status='paid'
        )

        # Invoice 2: Partially Paid ($300.00 total, $100 paid, $200 outstanding)
        inv2 = Invoice(
            invoice_number='INV-2026-002',
            subscription_id=sub2.id,
            customer_id=cust2.id,
            invoice_date=today - timedelta(days=20),
            due_date=today + timedelta(days=10),
            subtotal=Decimal('300.00'),
            tax_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('300.00'),
            status='confirmed',
            payment_status='partially_paid'
        )

        # Invoice 3: Overdue ($450.00 total, 14 days overdue)
        inv3 = Invoice(
            invoice_number='INV-2026-003',
            subscription_id=sub3.id,
            customer_id=cust3.id,
            invoice_date=today - timedelta(days=30),
            due_date=today - timedelta(days=14),
            subtotal=Decimal('450.00'),
            tax_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('450.00'),
            status='confirmed',
            payment_status='overdue'
        )

        # Invoice 4: Fresh Unpaid ($200.00, due in 15 days)
        inv4 = Invoice(
            invoice_number='INV-2026-004',
            subscription_id=sub2.id,
            customer_id=cust2.id,
            invoice_date=today - timedelta(days=2),
            due_date=today + timedelta(days=13),
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            status='confirmed',
            payment_status='unpaid'
        )

        db.session.add_all([inv1, inv2, inv3, inv4])
        db.session.commit()

        # 7. Payments (Member 4)
        # Payment 1: Full settlement for INV-2026-001
        pay1 = Payment(
            payment_reference='PAY-20260901-ACME01',
            customer_id=cust1.id,
            invoice_id=inv1.id,
            amount=Decimal('2200.00'),
            payment_date=today - timedelta(days=40),
            payment_method='bank_transfer',
            notes='Wire transfer settled via Chase Bank #TX-90218'
        )

        # Payment 2: Partial payment for INV-2026-002
        pay2 = Payment(
            payment_reference='PAY-20261015-CAFE01',
            customer_id=cust2.id,
            invoice_id=inv2.id,
            amount=Decimal('100.00'),
            payment_date=today - timedelta(days=15),
            payment_method='credit_card',
            notes='Installment 1 paid via Mastercard *8832'
        )

        db.session.add_all([pay1, pay2])
        db.session.commit()

        # Refresh invoice statuses
        inv1.refresh_payment_status()
        inv2.refresh_payment_status()
        inv3.refresh_payment_status()
        inv4.refresh_payment_status()
        db.session.commit()

        print("[OK] Seeding completed successfully into MySQL database!")
        print(f"Total Revenue Received: ${pay1.amount + pay2.amount:,.2f}")
        print(f"Active Subscriptions: {Subscription.query.filter_by(status='active').count()}")

if __name__ == '__main__':
    seed()
