"""
Billing service — idempotent invoice generation for subscriptions.
Managed by Sridhya's module.

NOTE: For the hackathon MVP, invoice generation is triggered manually via a route.
      A scheduled task (e.g. APScheduler / Celery beat) would call generate_due_invoices()
      automatically in a production deployment.
"""
from datetime import date, timedelta
from app.extensions import db
from app.models.subscription import Subscription
from app.models.invoice import Invoice, InvoiceLine
from app.models.plan import SubscriptionPlan


def calculate_billing_period(subscription: Subscription, reference_date: date = None):
    """
    Calculate the billing period (start, end) for a subscription given a reference date.
    The reference date defaults to next_billing_date or today.
    """
    ref = reference_date or subscription.next_billing_date or date.today()
    plan = subscription.plan
    if not plan:
        return ref, ref

    interval = plan.billing_interval
    count = plan.interval_count or 1

    if interval == SubscriptionPlan.INTERVAL_DAILY:
        period_end = ref + timedelta(days=count) - timedelta(days=1)
    elif interval == SubscriptionPlan.INTERVAL_WEEKLY:
        period_end = ref + timedelta(weeks=count) - timedelta(days=1)
    elif interval == SubscriptionPlan.INTERVAL_MONTHLY:
        # Advance month by count
        month = ref.month - 1 + count
        year = ref.year + month // 12
        month = month % 12 + 1
        import calendar
        day = min(ref.day, calendar.monthrange(year, month)[1])
        next_start = date(year, month, day)
        period_end = next_start - timedelta(days=1)
    elif interval == SubscriptionPlan.INTERVAL_QUARTERLY:
        month = ref.month - 1 + (3 * count)
        year = ref.year + month // 12
        month = month % 12 + 1
        import calendar
        day = min(ref.day, calendar.monthrange(year, month)[1])
        next_start = date(year, month, day)
        period_end = next_start - timedelta(days=1)
    elif interval == SubscriptionPlan.INTERVAL_YEARLY:
        import calendar
        try:
            next_start = date(ref.year + count, ref.month, ref.day)
        except ValueError:
            next_start = date(ref.year + count, ref.month,
                              calendar.monthrange(ref.year + count, ref.month)[1])
        period_end = next_start - timedelta(days=1)
    else:
        period_end = ref + timedelta(days=30)

    return ref, period_end


def advance_billing_date(subscription: Subscription):
    """Advance next_billing_date by one billing period."""
    current = subscription.next_billing_date or date.today()
    _, period_end = calculate_billing_period(subscription, current)
    subscription.next_billing_date = period_end + timedelta(days=1)


def invoice_already_exists(subscription_id: int, period_start: date, period_end: date) -> bool:
    """
    Idempotency guard: returns True if an invoice already exists for this
    subscription and billing period.
    """
    return Invoice.query.filter_by(
        subscription_id=subscription_id,
        billing_period_start=period_start,
        billing_period_end=period_end,
    ).first() is not None


def _generate_invoice_number():
    """Generate unique INV-YYYYMMDD-XXXX number."""
    today = date.today().strftime('%Y%m%d')
    prefix = f"INV-{today}-"
    last = (
        Invoice.query
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.id.desc())
        .first()
    )
    if last:
        try:
            seq = int(last.invoice_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def create_invoice_for_period(subscription: Subscription, period_start: date, period_end: date) -> Invoice:
    """
    Create a confirmed-draft Invoice for a single billing period of a subscription.
    Idempotent: will not create a duplicate if one already exists.
    Returns the existing or newly created invoice.
    """
    if invoice_already_exists(subscription.id, period_start, period_end):
        return Invoice.query.filter_by(
            subscription_id=subscription.id,
            billing_period_start=period_start,
            billing_period_end=period_end,
        ).first()

    invoice_date = date.today()
    due_date = subscription.due_date_for_invoice(invoice_date)

    invoice = Invoice(
        invoice_number=_generate_invoice_number(),
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        issue_date=invoice_date,
        due_date=due_date,
        billing_period_start=period_start,
        billing_period_end=period_end,
        status=Invoice.STATUS_DRAFT,
    )
    db.session.add(invoice)
    db.session.flush()  # get invoice.id

    # Build line item
    qty = subscription.quantity or 1
    price = float(subscription.unit_price or 0)
    plan_name = subscription.plan.name if subscription.plan else "Subscription"
    product_name = subscription.product.name if subscription.product else ""
    description = (
        f"{plan_name}"
        + (f" — {product_name}" if product_name else "")
        + f" | {period_start.strftime('%b %d, %Y')} – {period_end.strftime('%b %d, %Y')}"
    )

    line = InvoiceLine(
        invoice_id=invoice.id,
        product_id=subscription.product_id,
        tax_id=subscription.tax_id,
        description=description,
        quantity=qty,
        unit_price=price,
    )
    db.session.add(line)
    db.session.flush()

    # Calculate totals
    invoice.recalculate_totals()
    db.session.add(invoice)

    return invoice


def generate_due_invoices(dry_run: bool = False) -> list:
    """
    Find all ACTIVE subscriptions whose next_billing_date is today or in the past,
    generate one invoice per due period, advance next_billing_date, and return
    the list of created invoices.

    This is the MANUAL trigger function for MVP.
    In production, this would be scheduled via APScheduler / Celery beat.
    """
    today = date.today()
    active_subs = Subscription.query.filter(
        Subscription.status == Subscription.STATUS_ACTIVE,
        Subscription.next_billing_date <= today,
    ).all()

    created_invoices = []

    for sub in active_subs:
        # Skip if subscription has ended
        if sub.end_date and sub.end_date < today:
            if not dry_run:
                sub.status = Subscription.STATUS_EXPIRED
                db.session.add(sub)
            continue

        # Generate all overdue periods (catches up if billing was missed)
        max_iterations = 60  # safety limit
        i = 0
        while sub.next_billing_date and sub.next_billing_date <= today and i < max_iterations:
            period_start, period_end = calculate_billing_period(sub, sub.next_billing_date)

            # Don't generate past the subscription end
            if sub.end_date and period_start > sub.end_date:
                break

            if not dry_run:
                inv = create_invoice_for_period(sub, period_start, period_end)
                created_invoices.append(inv)
                advance_billing_date(sub)
                db.session.add(sub)
            else:
                created_invoices.append({
                    'subscription': sub.subscription_number,
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                })
                advance_billing_date(sub)
            i += 1

    if not dry_run:
        db.session.commit()

    return created_invoices
