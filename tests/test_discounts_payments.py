import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date, timedelta
from decimal import Decimal
from flask import Flask
from extensions import db
from models.user import User
from models.product import Product
from models.plan import Plan
from models.subscription import Subscription
from models.invoice import Invoice
from models.invoice_line import InvoiceLine
from models.discount import Discount
from models.payment import Payment
from models.invoice_discount import InvoiceDiscount
from services.discount_service import DiscountService, DiscountValidationError
from services.payment_service import PaymentService, PaymentValidationError
from services.report_service import ReportService

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def setup_data(app):
    with app.app_context():
        admin = User(name='Admin User', email='admin@test.com', password_hash='hash', role='admin')
        customer = User(name='Shop Customer', email='customer@test.com', password_hash='hash', role='customer')
        db.session.add_all([admin, customer])
        db.session.commit()

        product = Product(name='Standard SaaS', sales_price=Decimal('100.00'), cost_price=Decimal('30.00'))
        db.session.add(product)
        db.session.commit()

        plan = Plan(name='Monthly Plan', billing_interval='monthly', cost=Decimal('100.00'), min_quantity=1)
        db.session.add(plan)
        db.session.commit()

        sub = Subscription(
            subscription_number='SUB-001',
            customer_id=customer.id,
            plan_id=plan.id,
            start_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            status='active'
        )
        db.session.add(sub)
        db.session.commit()

        invoice = Invoice(
            invoice_number='INV-2026-001',
            subscription_id=sub.id,
            customer_id=customer.id,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            status='confirmed',
            payment_status='unpaid'
        )
        db.session.add(invoice)
        db.session.commit()

        line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=product.id,
            description='Standard SaaS Seats',
            quantity=2,
            unit_price=Decimal('100.00'),
            subtotal=Decimal('200.00'),
            total=Decimal('200.00')
        )
        db.session.add(line)
        db.session.commit()

        return {
            'admin_id': admin.id,
            'customer_id': customer.id,
            'product_id': product.id,
            'plan_id': plan.id,
            'subscription_id': sub.id,
            'invoice_id': invoice.id
        }

def test_fixed_and_percentage_discounts(app, setup_data):
    with app.app_context():
        invoice = Invoice.query.get(setup_data['invoice_id'])

        # 1. Percentage discount: 20% off $200 = $40 deduction
        disc_pct = Discount(
            name='20% Off',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            min_purchase_amount=Decimal('50.00'),
            min_quantity=1,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            scope='subscription',
            is_active=True
        )
        db.session.add(disc_pct)
        db.session.commit()

        deduction = disc_pct.calculate_discount_amount(invoice.subtotal)
        assert deduction == Decimal('40.00')

        # 2. Fixed discount: $50 off
        disc_fixed = Discount(
            name='$50 Off',
            discount_type='fixed',
            discount_value=Decimal('50.00'),
            min_purchase_amount=Decimal('100.00'),
            min_quantity=1,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            scope='subscription',
            is_active=True
        )
        db.session.add(disc_fixed)
        db.session.commit()

        deduction_fixed = disc_fixed.calculate_discount_amount(invoice.subtotal)
        assert deduction_fixed == Decimal('50.00')

def test_discount_cannot_reduce_below_zero(app, setup_data):
    with app.app_context():
        invoice = Invoice.query.get(setup_data['invoice_id'])
        # Fixed discount of $500 on a $200 invoice
        big_disc = Discount(
            name='Huge $500 Off',
            discount_type='fixed',
            discount_value=Decimal('500.00'),
            min_purchase_amount=Decimal('0.00'),
            min_quantity=0,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            scope='subscription',
            is_active=True
        )
        db.session.add(big_disc)
        db.session.commit()

        updated_inv, deduction = DiscountService.apply_discount_to_invoice(invoice, big_disc)
        assert deduction == Decimal('200.00')
        assert updated_inv.total_amount == Decimal('0.00')
        assert updated_inv.total_amount >= Decimal('0.00')

def test_expired_and_exhausted_discounts(app, setup_data):
    with app.app_context():
        invoice = Invoice.query.get(setup_data['invoice_id'])
        
        # Expired discount
        expired_disc = Discount(
            name='Expired Discount',
            discount_type='fixed',
            discount_value=Decimal('10.00'),
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1),
            scope='subscription',
            is_active=True
        )
        db.session.add(expired_disc)
        db.session.commit()

        with pytest.raises(DiscountValidationError, match="expired"):
            DiscountService.apply_discount_to_invoice(invoice, expired_disc)

        # Exhausted quota discount
        exhausted_disc = Discount(
            name='Quota Discount',
            discount_type='fixed',
            discount_value=Decimal('10.00'),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=10),
            max_usage_limit=1,
            current_usage_count=1,
            scope='subscription',
            is_active=True
        )
        db.session.add(exhausted_disc)
        db.session.commit()

        with pytest.raises(DiscountValidationError, match="exhausted"):
            DiscountService.apply_discount_to_invoice(invoice, exhausted_disc)

def test_payment_recording_and_overpayment_prevention(app, setup_data):
    with app.app_context():
        invoice = Invoice.query.get(setup_data['invoice_id'])
        assert invoice.outstanding_amount == Decimal('200.00')
        assert invoice.payment_status == 'unpaid'

        # 1. Test Overpayment Prevention
        with pytest.raises(PaymentValidationError, match="Overpayment blocked"):
            PaymentService.record_payment(
                invoice_id=invoice.id,
                amount=Decimal('250.00'),
                payment_method='bank_transfer'
            )

        # 2. Test Partial Payment: record $80
        payment1 = PaymentService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('80.00'),
            payment_method='bank_transfer',
            notes='First installment'
        )
        invoice = Invoice.query.get(setup_data['invoice_id'])
        assert payment1.amount == Decimal('80.00')
        assert invoice.total_paid == Decimal('80.00')
        assert invoice.outstanding_amount == Decimal('120.00')
        assert invoice.payment_status == 'partially_paid'

        # 3. Test Full Settlement: record remaining $120
        payment2 = PaymentService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('120.00'),
            payment_method='credit_card',
            notes='Final settlement'
        )
        invoice = Invoice.query.get(setup_data['invoice_id'])
        assert invoice.total_paid == Decimal('200.00')
        assert invoice.outstanding_amount == Decimal('0.00')
        assert invoice.payment_status == 'paid'

def test_overdue_tracking_and_exclusion_of_paid(app, setup_data):
    with app.app_context():
        customer_id = setup_data['customer_id']
        
        # Create an invoice past due date (10 days ago) with $150
        overdue_inv = Invoice(
            invoice_number='INV-OVERDUE-01',
            customer_id=customer_id,
            invoice_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            subtotal=Decimal('150.00'),
            total_amount=Decimal('150.00'),
            status='confirmed',
            payment_status='overdue'
        )
        db.session.add(overdue_inv)
        db.session.commit()

        # Should appear in overdue tracking
        overdue_list = PaymentService.get_tracked_invoices(status_filter='overdue')
        assert any(i.id == overdue_inv.id for i in overdue_list)

        # Pay invoice in full
        PaymentService.record_payment(
            invoice_id=overdue_inv.id,
            amount=Decimal('150.00'),
            payment_method='cash'
        )

        # MUST be excluded from overdue tracking once fully paid!
        updated_overdue_list = PaymentService.get_tracked_invoices(status_filter='overdue')
        assert not any(i.id == overdue_inv.id for i in updated_overdue_list)

def test_revenue_report_calculated_from_actual_payments(app, setup_data):
    with app.app_context():
        invoice = Invoice.query.get(setup_data['invoice_id'])
        
        summary_initial = ReportService.get_revenue_summary()
        assert summary_initial['total_revenue_received'] == 0.00

        # Record a payment of $125
        PaymentService.record_payment(
            invoice_id=invoice.id,
            amount=Decimal('125.00'),
            payment_method='stripe'
        )

        # Revenue received must reflect actual payments received ($125)
        summary_after = ReportService.get_revenue_summary()
        assert summary_after['total_revenue_received'] == 125.00
        assert summary_after['active_subscriptions_count'] == 1
