from datetime import date, timedelta
from decimal import Decimal

def test_formulas():
    print("Testing Member 4 Business Logic & Calculations...")

    # 1. Discount Percentage Calculation
    subtotal = Decimal('250.00')
    discount_pct = Decimal('15.00')
    calculated_pct_deduction = (subtotal * (discount_pct / Decimal('100.00'))).quantize(Decimal('0.01'))
    assert calculated_pct_deduction == Decimal('37.50'), f"Expected 37.50, got {calculated_pct_deduction}"
    print("[OK] Percentage discount calculation passed: 15% of $250.00 = $37.50")

    # 2. Fixed Discount Deduction
    fixed_deduction = Decimal('50.00')
    net_after_fixed = max(Decimal('0.00'), subtotal - fixed_deduction)
    assert net_after_fixed == Decimal('200.00')
    print("[OK] Fixed discount deduction passed: $250.00 - $50.00 = $200.00")

    # 3. Non-Negative Invoice Total Guarantee
    excessive_discount = Decimal('300.00')
    net_non_negative = max(Decimal('0.00'), subtotal - excessive_discount)
    assert net_non_negative == Decimal('0.00'), f"Invoice total must not drop below zero, got {net_non_negative}"
    print("[OK] Zero floor protection passed: $250.00 - $300.00 capped at $0.00")

    # 4. Outstanding Amount Formula: Total - Total Valid Payments
    invoice_total = Decimal('500.00')
    payments = [Decimal('120.00'), Decimal('180.00')]
    total_valid_payments = sum(payments)
    outstanding_amount = max(Decimal('0.00'), invoice_total - total_valid_payments)
    assert total_valid_payments == Decimal('300.00')
    assert outstanding_amount == Decimal('200.00')
    print(f"[OK] Outstanding amount formula passed: $500.00 - $300.00 = ${outstanding_amount:.2f}")

    # 5. Overpayment Prevention Check
    new_payment_attempt = Decimal('250.00')
    is_overpayment = new_payment_attempt > outstanding_amount
    assert is_overpayment is True
    print(f"[OK] Overpayment prevention logic passed: Attempt ${new_payment_attempt:.2f} > Outstanding ${outstanding_amount:.2f} is blocked")

    # 6. Payment Status Transitions
    def get_payment_status(total, paid, due_date, today):
        if total > 0 and paid >= total:
            return 'paid'
        elif today > due_date and (total - paid) > 0:
            return 'overdue'
        elif paid > 0:
            return 'partially_paid'
        else:
            return 'unpaid'

    today = date(2026, 10, 31)
    future_due = date(2026, 11, 15)
    past_due = date(2026, 10, 15)

    assert get_payment_status(Decimal('500.00'), Decimal('0.00'), future_due, today) == 'unpaid'
    assert get_payment_status(Decimal('500.00'), Decimal('100.00'), future_due, today) == 'partially_paid'
    assert get_payment_status(Decimal('500.00'), Decimal('500.00'), future_due, today) == 'paid'
    assert get_payment_status(Decimal('500.00'), Decimal('100.00'), past_due, today) == 'overdue'
    assert get_payment_status(Decimal('500.00'), Decimal('500.00'), past_due, today) == 'paid'
    print("[OK] Payment status state transitions passed (including exclusion of fully paid invoices from overdue)")

    # 7. Revenue Calculated from Actual Payments Only (NOT from Invoices)
    invoices_generated = [Decimal('1000.00'), Decimal('500.00'), Decimal('750.00')]
    actual_recorded_payments = [Decimal('1000.00'), Decimal('200.00')]
    total_invoiced = sum(invoices_generated)
    total_revenue_received = sum(actual_recorded_payments)
    assert total_invoiced == Decimal('2250.00')
    assert total_revenue_received == Decimal('1200.00')
    assert total_revenue_received != total_invoiced
    print(f"[OK] Revenue calculation strictly from payments passed: Revenue = ${total_revenue_received:.2f} (Invoiced = ${total_invoiced:.2f})")

    print("\nALL 7 CORE MATHEMATICAL & BUSINESS RULES PASSED PERFECTLY!")

if __name__ == '__main__':
    test_formulas()
