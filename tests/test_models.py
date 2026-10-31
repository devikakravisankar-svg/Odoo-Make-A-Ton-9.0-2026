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

def test_models_and_relationships(app):
    with app.app_context():
        # 1. User
        admin = User(username='admin_m', email='admin_m@test.com', full_name='Admin M', role=User.ROLE_ADMIN)
        admin.set_password('Admin@Test2026!')
        cust = User(username='cust_m', email='cust_m@test.com', full_name='Cust M', role=User.ROLE_CUSTOMER)
        cust.set_password('Cust@Test2026!')
        db.session.add_all([admin, cust])
        db.session.flush()

        # 2. Product & ProductVariant
        prod = Product(name='ERP Module', code='ERP-MOD', base_price=100.00)
        db.session.add(prod)
        db.session.flush()

        variant = ProductVariant(product_id=prod.id, name='10 Seats', sku='ERP-MOD-10S', price=100.00)
        db.session.add(variant)

        # 3. SubscriptionPlan
        plan = SubscriptionPlan(name='Gold Plan', code='GOLD-PLAN', base_price=99.00, billing_interval=SubscriptionPlan.INTERVAL_MONTHLY)
        db.session.add(plan)
        db.session.flush()

        # 4. Quotation
        quot = Quotation(quotation_number='QUOT-001', customer_id=cust.id, total_amount=99.00)
        db.session.add(quot)

        # 5. Subscription
        sub = Subscription(subscription_number='SUB-001', customer_id=cust.id, plan_id=plan.id, total_amount=99.00, start_date=date.today())
        db.session.add(sub)
        db.session.flush()

        # 6. Invoice & InvoiceLine
        inv = Invoice(invoice_number='INV-001', customer_id=cust.id, subscription_id=sub.id, due_date=date.today(), total_amount=99.00)
        db.session.add(inv)
        db.session.flush()

        line = InvoiceLine(invoice_id=inv.id, product_id=prod.id, description='Monthly Gold Plan', quantity=1, unit_price=99.00, line_total=99.00)
        db.session.add(line)

        # 7. Tax
        tax = Tax(name='GST 18%', rate_percentage=18.00)
        db.session.add(tax)

        # 8. Discount (Admin created)
        disc = Discount(code='FESTIVE10', discount_type=Discount.TYPE_PERCENTAGE, value=10.00, created_by=admin.id)
        db.session.add(disc)

        # 9. Payment
        pay = Payment(payment_reference='PAY-TXN-001', invoice_id=inv.id, customer_id=cust.id, amount=99.00, status=Payment.STATUS_SUCCESSFUL)
        db.session.add(pay)

        db.session.commit()

        # Assertions
        assert prod.variants.count() == 1
        assert cust.subscriptions.count() == 1
        assert cust.invoices.count() == 1
        assert inv.lines.count() == 1
        assert inv.payments.count() == 1
        assert disc.creator.id == admin.id
        assert disc.is_valid_now is True
