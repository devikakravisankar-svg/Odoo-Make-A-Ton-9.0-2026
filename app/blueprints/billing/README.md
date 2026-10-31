# Discounts, Payments & Revenue Reports Module

**Assigned Member:** Fairooz  
**Blueprint Name:** `billing_bp`  
**URL Prefix:** `/billing`

## Models in Scope
- `Discount` (`app/models/discount.py`)
  - Fields: `id`, `code`, `discount_type` ('percentage', 'fixed'), `value`, `min_purchase_amount`, `valid_from`, `valid_until`, `usage_limit`, `times_used`, `is_active`, `created_by` (FK -> `User.id`), `created_at`
- `Payment` (`app/models/payment.py`)
  - Fields: `id`, `payment_reference`, `invoice_id` (FK -> `Invoice.id`), `customer_id` (FK -> `User.id`), `amount`, `payment_method` ('card', 'bank_transfer', 'upi', 'cash'), `status` ('successful', 'pending', 'failed', 'refunded'), `transaction_date`, `notes`
- `Tax` (`app/models/tax.py`)
  - Fields: `id`, `name`, `rate_percentage`, `is_active`, `description`, `created_at`

## Module Responsibilities
1. Discount rule management (**CRITICAL RULE:** Only Admin can create discount rules, staff can only view/apply).
2. Payment capture & verification (updating Invoice status to 'paid' or 'partially_paid').
3. Tax rate calculations.
4. Revenue and financial reports.

## Note for Fairooz
Please use `@admin_required` for routes that create or delete discount rules!
