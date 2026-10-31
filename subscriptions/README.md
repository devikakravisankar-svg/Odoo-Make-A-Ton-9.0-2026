# Quotations, Subscriptions & Invoices Module

**Assigned Member:** Sridhya  
**Blueprint Name:** `subscriptions_bp`  
**URL Prefix:** `/subscriptions`

## Models in Scope
- `Quotation` (`app/models/quotation.py`)
  - Fields: `id`, `quotation_number`, `customer_id`, `status` ('draft', 'sent', 'accepted', 'rejected', 'expired'), `subtotal`, `tax_amount`, `discount_amount`, `total_amount`, `valid_until`, `notes`, `created_at`
- `Subscription` (`app/models/subscription.py`)
  - Fields: `id`, `subscription_number`, `customer_id`, `plan_id`, `status` ('active', 'pending', 'paused', 'cancelled', 'expired'), `start_date`, `next_billing_date`, `end_date`, `auto_renew`, `total_amount`, `created_at`
- `Invoice` (`app/models/invoice.py`)
  - Fields: `id`, `invoice_number`, `customer_id`, `subscription_id`, `issue_date`, `due_date`, `status` ('draft', 'pending', 'paid', 'partially_paid', 'overdue', 'cancelled'), `subtotal`, `tax_amount`, `discount_amount`, `total_amount`, `amount_paid`, `created_at`
- `InvoiceLine` (`app/models/invoice.py`)
  - Fields: `id`, `invoice_id`, `product_id`, `description`, `quantity`, `unit_price`, `line_total`

## Module Responsibilities
1. Quotation creation, sending, and conversion into active subscriptions.
2. Subscription lifecycle (activate, pause, renew, cancel).
3. Recurring invoice generation with line items.
4. Tracking invoice statuses and due dates.

## Note for Sridhya
Please write your routes inside this directory. Do not alter shared models without team coordination.
