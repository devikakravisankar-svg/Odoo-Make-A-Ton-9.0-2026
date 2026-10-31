# Subscription Management System - Odoo Make-A-Ton 9.0 (2026)

A modular, enterprise-grade Subscription Management System built with **Python Flask**, **MySQL**, **SQLAlchemy ORM**, **Flask-Login**, and vanilla JavaScript.

---

##  Team & Module Ownership

| Member | Role | Assigned Modules & Scope |
| :--- | :--- | :--- |
| **Devika K** (Team Lead) | Foundation & Integration | Project factory, MySQL config, Auth, RBAC, Dashboard, Customer Portal, Team Blueprint Integration |
| **Nidha Sherin K** | Core Catalog | Product Management, Product Variants, Subscription Plans (`app/blueprints/products/`) |
| **Sridhya Deleep Kumar** | Order & Lifecycle | Quotations, Subscriptions lifecycle, Invoices & Line Items (`app/blueprints/subscriptions/`) |
| **Fairooz Fizal Moilingantakath** | Finance & Reporting | Discounts/Coupons, Payment transactions, Taxes, Revenue Reports (`app/blueprints/billing/`) |

---

##  Architecture & Shared Folder Structure

The application adopts the **Application Factory** pattern with modular Flask Blueprints:

```
Odoo-Make-A-Ton-9.0-2026/
├── .env.example              # Sample environment configuration template
├── .gitignore                # Git ignore rules (secrets & temp files excluded)
├── requirements.txt          # Python dependencies
├── README.md                 # Complete system documentation & contracts
├── run.py                    # Server startup script
├── app.py                    # Root alias entry point
├── app/
│   ├── __init__.py           # Application Factory (create_app) & CLI commands
│   ├── config.py             # Config classes (Base, Development, Testing, Production)
│   ├── extensions.py         # SQLAlchemy & Flask-Login instances
│   ├── models/               # Centralized shared SQLAlchemy models
│   │   ├── __init__.py       # Central model exports
│   │   ├── user.py           # User model with role methods
│   │   ├── product.py        # Product and ProductVariant
│   │   ├── plan.py           # SubscriptionPlan
│   │   ├── quotation.py      # Quotation
│   │   ├── subscription.py   # Subscription
│   │   ├── invoice.py        # Invoice and InvoiceLine
│   │   ├── tax.py            # Tax
│   │   ├── discount.py       # Discount (Admin created)
│   │   └── payment.py        # Payment
│   ├── utils/
│   │   ├── decorators.py     # @admin_required, @staff_required, @customer_required
│   │   ├── validators.py     # Password complexity validation
│   │   └── email_service.py  # Password reset tokens & configurable SMTP delivery
│   ├── blueprints/
│   │   ├── auth/             # Devika: Auth (register, login, logout, reset password)
│   │   ├── dashboard/        # Devika: Executive Dashboard & Staff management
│   │   ├── portal/           # Devika: Customer Portal (profile, products, invoices, subs)
│   │   ├── products/         # Nidha: Product & Plan management
│   │   ├── subscriptions/    # Sridhya: Quotations, Subscriptions & Invoices
│   │   └── billing/          # Fairooz: Discounts, Payments & Reports
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── portal/
│   │   ├── products/
│   │   ├── subscriptions/
│   │   └── billing/
│   └── static/
│       ├── css/style.css     # Clean, responsive Odoo-inspired styling
│       └── js/main.js        # Vanilla JS live password validation & UI helpers
└── tests/                    # Comprehensive Pytest automated test suite
    ├── conftest.py
    ├── test_validators.py
    ├── test_auth.py
    ├── test_models.py
    └── test_roles.py
```

---

##  Shared Database Model Contracts

All members must use these exact field names and types to ensure zero integration friction:

### 1. `User` (`app.models.user.User`)
- `id` (PK, Integer)
- `username` (String 80, Unique, Not Null)
- `email` (String 120, Unique, Not Null)
- `password_hash` (String 255, Not Null)
- `full_name` (String 120, Not Null)
- `phone` (String 20, Nullable)
- `role` (String 20, Enum: `'admin'`, `'staff'`, `'customer'`)
- `is_active` (Boolean, Default: True)
- `created_at` (DateTime), `updated_at` (DateTime)

### 2. `Product` & `ProductVariant` (`app.models.product`)
- **Product**: `id` (PK), `name` (String 150), `code` (String 50, Unique), `description` (Text), `base_price` (Numeric 10,2), `is_active` (Boolean)
- **ProductVariant**: `id` (PK), `product_id` (FK -> `products.id`), `name` (String 100), `sku` (String 64, Unique), `price` (Numeric 10,2), `attributes` (JSON), `is_active` (Boolean)

### 3. `SubscriptionPlan` (`app.models.plan.SubscriptionPlan`)
- `id` (PK), `name` (String 100), `code` (String 50, Unique), `description` (Text), `billing_interval` (String 20: `'monthly'`, `'yearly'`, etc.), `interval_count` (Integer, Default 1), `base_price` (Numeric 10,2), `trial_days` (Integer), `is_active` (Boolean)

### 4. `Quotation` (`app.models.quotation.Quotation`)
- `id` (PK), `quotation_number` (String 50, Unique), `customer_id` (FK -> `users.id`), `status` (String 20: `'draft'`, `'sent'`, `'accepted'`, `'rejected'`, `'expired'`), `subtotal`, `tax_amount`, `discount_amount`, `total_amount` (Numeric 10,2), `valid_until` (Date), `notes` (Text)

### 5. `Subscription` (`app.models.subscription.Subscription`)
- `id` (PK), `subscription_number` (String 50, Unique), `customer_id` (FK -> `users.id`), `plan_id` (FK -> `subscription_plans.id`), `status` (String 20: `'active'`, `'pending'`, `'paused'`, `'cancelled'`, `'expired'`), `start_date` (Date), `next_billing_date` (Date), `end_date` (Date), `auto_renew` (Boolean), `total_amount` (Numeric 10,2)

### 6. `Invoice` & `InvoiceLine` (`app.models.invoice`)
- **Invoice**: `id` (PK), `invoice_number` (String 50, Unique), `customer_id` (FK -> `users.id`), `subscription_id` (FK -> `subscriptions.id`, Nullable), `issue_date` (Date), `due_date` (Date), `status` (String 20: `'draft'`, `'pending'`, `'paid'`, `'partially_paid'`, `'overdue'`, `'cancelled'`), `subtotal`, `tax_amount`, `discount_amount`, `total_amount`, `amount_paid` (Numeric 10,2)
- **InvoiceLine**: `id` (PK), `invoice_id` (FK -> `invoices.id`), `product_id` (FK -> `products.id`), `description` (String 255), `quantity` (Integer), `unit_price`, `line_total` (Numeric 10,2)

### 7. `Tax` (`app.models.tax.Tax`)
- `id` (PK), `name` (String 80), `rate_percentage` (Numeric 5,2), `is_active` (Boolean), `description` (String 255)

### 8. `Discount` (`app.models.discount.Discount`)
- `id` (PK), `code` (String 50, Unique), `discount_type` (String 20: `'percentage'`, `'fixed'`), `value` (Numeric 10,2), `min_purchase_amount` (Numeric 10,2), `valid_from` (Date), `valid_until` (Date), `usage_limit` (Integer), `times_used` (Integer), `is_active` (Boolean), `created_by` (FK -> `users.id` - **Admin Only**)

### 9. `Payment` (`app.models.payment.Payment`)
- `id` (PK), `payment_reference` (String 64, Unique), `invoice_id` (FK -> `invoices.id`), `customer_id` (FK -> `users.id`), `amount` (Numeric 10,2), `payment_method` (String 30: `'card'`, `'bank_transfer'`, `'upi'`, `'cash'`), `status` (String 20: `'successful'`, `'pending'`, `'failed'`, `'refunded'`), `transaction_date` (DateTime), `notes` (Text)

---

##  Security & Role-Based Access Control (RBAC)

### Password Complexity Rules
Enforced both via frontend validation and backend validation (`app.utils.validators.validate_password_strength`):
1. Length: **More than 8 characters** (> 8).
2. At least one **uppercase** letter (`A-Z`).
3. At least one **lowercase** letter (`a-z`).
4. At least one **special character** (e.g. `!@#$%^&*()_+-=[]{}|;:,.<>?`).

### Permissions Matrix
- **Admin**: Full access. Only Admin can create internal staff accounts and discount rules.
- **Internal Staff**: Operational management of products, subscriptions, and invoices.
- **Customer**: Access restricted strictly to their own profile, subscriptions, invoices, and payments. Customers cannot view or access records belonging to other customers.

---

##  Getting Started

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.0+

### 2. Environment Setup
Create your local environment file from `.env.example`:
```bash
cp .env.example .env
```

Edit `.env` with your MySQL credentials:
```env
SECRET_KEY=your-secure-random-key
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=subscription_management_db

# Email settings (optional, console fallback enabled if unconfigured)
MAIL_SERVER=
MAIL_USERNAME=
MAIL_PASSWORD=
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Initialization & Seeding
Create MySQL database:
```sql
CREATE DATABASE subscription_management_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Run CLI commands:
```bash
# 1. Create all MySQL tables
flask init-db

# 2. Seed initial Administrator account (admin / Admin@Odoo2026!)
flask seed-admin

# 3. Seed demo products, plans, and taxes
flask seed-demo
```

### 5. Run Development Server
```bash
python run.py
```
Visit: `http://localhost:5000`

---

##  Automated Testing

Run the test suite with verbose output:
```bash
pytest -v
```
All 18 tests cover:
- Customer registration and password complexity validation
- Login/logout and password reset token generation
- RBAC permissions enforcement and customer data isolation
- Full ORM model persistence and relational integrity

---

##  Teammate Contribution Guidelines

1. **Work within your assigned directory**:
   - Nidha: `app/blueprints/products/`
   - Sridhya: `app/blueprints/subscriptions/`
   - Fairooz: `app/blueprints/billing/`
2. **Never modify `app/models/` or core auth files** without consulting the team.
3. **Use the shared decorators**:
   - `@staff_required` for staff/admin endpoints.
   - `@admin_required` for admin-only operations (e.g., Discount creation).
4. **Never commit `.env` or plain-text credentials**.
