from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func
from extensions import db
from models.payment import Payment
from models.invoice import Invoice
from models.subscription import Subscription
from models.user import User

class ReportService:

    @staticmethod
    def get_revenue_summary(start_date=None, end_date=None):
        """
        Computes high-level financial KPIs:
        1. Total revenue received: Must be calculated from actual successful payment records!
        2. Total outstanding invoice amount (Total - Valid Payments for all active/unpaid invoices)
        3. Total overdue invoice amount (Outstanding amount where due_date < today)
        4. Active subscription count
        """
        today = date.today()

        # Parse date range for filtering
        if isinstance(start_date, str) and start_date.strip():
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = None

        if isinstance(end_date, str) and end_date.strip():
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = None

        # 1. Total Revenue Received (FROM ACTUAL PAYMENTS ONLY)
        payment_query = db.session.query(func.coalesce(func.sum(Payment.amount), 0.00))
        if start_date:
            payment_query = payment_query.filter(Payment.payment_date >= start_date)
        if end_date:
            payment_query = payment_query.filter(Payment.payment_date <= end_date)
        total_revenue_received = Decimal(str(payment_query.scalar() or 0.00))

        # 2. Active Subscription Count
        active_subscriptions_count = Subscription.query.filter_by(status='active').count()

        # 3. Invoices analysis for Outstanding & Overdue
        invoices = Invoice.query.filter(Invoice.status.in_(['confirmed', 'paid'])).all()

        total_outstanding_amount = Decimal('0.00')
        total_overdue_amount = Decimal('0.00')
        overdue_invoices_count = 0
        unpaid_invoices_count = 0
        paid_invoices_count = 0
        partially_paid_count = 0

        for inv in invoices:
            inv.refresh_payment_status()
            bal = inv.outstanding_amount
            
            if bal > Decimal('0.00'):
                total_outstanding_amount += bal
                if inv.due_date < today:
                    total_overdue_amount += bal
                    overdue_invoices_count += 1
                
                if inv.total_paid > Decimal('0.00'):
                    partially_paid_count += 1
                else:
                    unpaid_invoices_count += 1
            else:
                paid_invoices_count += 1

        return {
            'total_revenue_received': float(total_revenue_received),
            'total_outstanding_amount': float(total_outstanding_amount),
            'total_overdue_amount': float(total_overdue_amount),
            'active_subscriptions_count': active_subscriptions_count,
            'overdue_invoices_count': overdue_invoices_count,
            'unpaid_invoices_count': unpaid_invoices_count,
            'partially_paid_count': partially_paid_count,
            'paid_invoices_count': paid_invoices_count,
            'total_invoices_tracked': len(invoices)
        }

    @staticmethod
    def get_revenue_timeline(start_date=None, end_date=None):
        """
        Aggregates revenue collected by date for charts/analytics.
        """
        if not end_date:
            end_date = date.today()
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date:
            start_date = end_date - timedelta(days=30)
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        # Group payments by payment_date
        records = db.session.query(
            Payment.payment_date,
            func.sum(Payment.amount).label('daily_total'),
            func.count(Payment.id).label('payment_count')
        ).filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).group_by(Payment.payment_date).order_by(Payment.payment_date.asc()).all()

        return [
            {
                'date': r.payment_date.isoformat(),
                'total': float(r.daily_total),
                'count': r.payment_count
            }
            for r in records
        ]

    @staticmethod
    def get_payment_methods_breakdown():
        """
        Breakdown of actual collected revenue by payment method.
        """
        records = db.session.query(
            Payment.payment_method,
            func.sum(Payment.amount).label('total_amount'),
            func.count(Payment.id).label('count')
        ).group_by(Payment.payment_method).all()

        return [
            {
                'method': r.payment_method.replace('_', ' ').title(),
                'raw_method': r.payment_method,
                'total': float(r.total_amount),
                'count': r.count
            }
            for r in records
        ]
