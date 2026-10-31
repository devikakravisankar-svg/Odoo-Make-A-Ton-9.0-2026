# Brightloop Subscription Management System
## Member 4: Discount & Payment Management Architecture

**Developer:** Fairooz (Member 4)  
**Branch:** `discounts-payments`  
**Stack:** Python Flask, MySQL, SQLAlchemy, HTML, CSS, Vanilla JS

---

### 1. Shared Database Model Contract (For Devika)
To maintain zero merge conflicts and ensure shared stability, all shared models are cleanly isolated:
- `models/user.py`: `User` with roles (`'admin'`, `'staff'`, `'customer'`).
- `models/product.py`: `Product` and `ProductVariant` (variant pricing additions, e.g., Odoo brand +$560).
- `models/plan.py`: `Plan` (intervals, costs, auto-close, pause, renew flags).
- `models/subscription.py`: `Subscription` (lifecycle states: `draft` -> `quotation` -> `confirmed` -> `active` -> `closed`).
- `models/invoice.py`: `Invoice` (totals, `status`: `draft`, `confirmed`, `paid`, `cancelled`; `payment_status`: `unpaid`, `partially_paid`, `paid`, `overdue`).
- `models/invoice_line.py`: `InvoiceLine` (line quantities, unit prices, taxes, totals).
- `models/discount.py`: `Discount` (fixed/percentage, min spend, min qty, start/end dates, max quotas, product vs subscription scope).
- `models/payment.py`: `Payment` (unique payment reference, invoice link, customer link, method, amount, date, notes).
- `models/invoice_discount.py`: `InvoiceDiscount` (audit trail preventing duplicate applications).

---

### 2. Sridhya's Invoice Billing Integration Points
During recurring billing or invoice generation, Sridhya can call:
```python
from services.discount_service import DiscountService

# 1. Apply eligible discount to an invoice
invoice, deduction = DiscountService.apply_discount_to_invoice(invoice, discount)

# 2. Or via internal JSON API endpoint:
# POST /discounts/api/apply
# Payload: { "invoice_id": 101, "discount_id": 5 }
```

---

### 3. Business Rules Implemented
1. **Discount Engine**:
   - Fixed and Percentage (`%`) calculations.
   - Enforces `start_date <= today <= end_date`.
   - Checks `subtotal >= min_purchase_amount` and `total_quantity >= min_quantity`.
   - Halts application once `current_usage_count >= max_usage_limit`.
   - Guarantees `invoice.total_amount >= 0.00` (zero-floor protection).
   - Only **Admin** can create, edit, or toggle discount rules.

2. **Payment Recording & Overpayment Prevention**:
   - Generates unique reference (e.g. `PAY-20261031-XXXX`).
   - Formula: $\text{Outstanding Amount} = \text{Invoice Total} - \sum \text{Valid Payments}$.
   - Blocks any payment where $\text{amount} > \text{outstanding amount}$.
   - Updates invoice state: `unpaid` -> `partially_paid` -> `paid` (or `overdue`).

3. **Outstanding & Overdue Tracking**:
   - Identifies past-due invoices with an unpaid balance.
   - **Strictly excludes fully paid invoices** from overdue calculations.
   - Dynamic filters by customer, date range, and status.

4. **Revenue Reports**:
   - Revenue received is **strictly calculated from actual payment records**:
     $$\text{Total Revenue} = \sum \text{Payment.amount}$$
   - Displays real-time KPIs: Collected Revenue, Outstanding Balance, Overdue Receivables, and Active Subscriptions.
   - Timeline analytics and payment method breakdown.

---

### 4. How to Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed demo data (creates admin, customer, products, subscriptions, invoices, discounts, and payments)
python seed_data.py

# 3. Launch Flask server
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.
