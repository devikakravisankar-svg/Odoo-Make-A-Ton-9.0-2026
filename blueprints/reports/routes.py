from flask import Blueprint, render_template, request, jsonify
from datetime import date, timedelta
from services.report_service import ReportService
from utils.auth_helper import get_current_user

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/revenue')
def revenue_reports():
    """
    Revenue & Billing Reports Dashboard:
    - Total revenue received from actual successful payment records
    - Outstanding balances
    - Overdue balances
    - Active subscriptions
    - Revenue timeline and payment method breakdown
    """
    current_user = get_current_user()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Default to past 30 days if not set
    if not start_date or not end_date:
        today = date.today()
        end_date = today.isoformat()
        start_date = (today - timedelta(days=30)).isoformat()

    kpis = ReportService.get_revenue_summary(start_date=start_date, end_date=end_date)
    timeline = ReportService.get_revenue_timeline(start_date=start_date, end_date=end_date)
    method_breakdown = ReportService.get_payment_methods_breakdown()

    return render_template(
        'billing/revenue_reports.html',
        kpis=kpis,
        timeline=timeline,
        method_breakdown=method_breakdown,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )

@reports_bp.route('/api/summary')
def api_revenue_summary():
    """JSON API endpoint for real-time dashboard updates."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = ReportService.get_revenue_summary(start_date=start_date, end_date=end_date)
    return jsonify(data)
