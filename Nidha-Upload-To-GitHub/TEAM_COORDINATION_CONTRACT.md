# Subscription Management System ? Team Coordination & Database Contract

**Author**: Nidha (Member 2 ? Product Management & Subscription Plan Management)  
**Coordinated with**: Devika (Team Leader ? Foundation & Core Architecture)  
**Downstream Consumers**: 
- Sridhya (Member 3 ? Quotations & Subscriptions)
- Fairooz (Member 4 ? Discounts & Invoicing/Payments)

---

## 1. Architectural Overview & Responsibilities

- **Devika (Team Leader)**: Core Flask application factory (`create_app`), global configuration (`config.py` targeting MySQL), database extension (`extensions.py`), base user authentication & roles.
- **Nidha (Member 2 ? This Module)**: Product catalogue, variants, variant price calculation, subscription plans, billing frequencies, availability rules, minimum quantity validation, product & plan APIs for quotation/subscription/discount integration.
- **Sridhya (Member 3)**: Quotation and subscription workflows. Relies on `Product`, `ProductVariant`, and `SubscriptionPlan` to populate quotation line items, calculate totals, and validate subscription constraints.
- **Fairooz (Member 4)**: Discount management and payment processing. Relies on `Product` records to define product-specific discounts, category discounts, and validate invoice pricing.

---

## 2. Shared Database Models Contract (MySQL / SQLAlchemy)

### A. `Product` Model (`products` table)
| Column Name | Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT AUTO_INCREMENT` | Primary Key, Indexed | Unique product identifier |
| `name` | `VARCHAR(150)` | NOT NULL, Indexed | Product display name |
| `code` | `VARCHAR(50)` | UNIQUE, NOT NULL, Indexed | Product code / SKU |
| `product_type` | `VARCHAR(20)` | NOT NULL, DEFAULT `'goods'` | Enum: `'goods'`, `'service'`, `'subscription'` |
| `base_price` | `DECIMAL(10, 2)` | NOT NULL, DEFAULT `0.00` | Base selling price (in ? INR), aliased as `sales_price` |
| `cost_price` | `DECIMAL(10, 2)` | NOT NULL, DEFAULT `0.00` | Cost of goods/service (in ? INR) |
| `description`| `TEXT` | NULLABLE | Detailed product overview |
| `notes` | `TEXT` | NULLABLE | Internal operational notes |
| `status` | `VARCHAR(20)` | NOT NULL, DEFAULT `'active'` | `'active'`, `'archived'`, `'inactive'` |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `True` | Active status flag |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Record creation timestamp |
| `updated_at` | `DATETIME` | NOT NULL, ON UPDATE `CURRENT_TIMESTAMP` | Last updated timestamp |

**Relationships & Methods**:
- `variants`: `db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan', lazy='dynamic')`
- `plans`: `db.relationship('SubscriptionPlan', backref='product', lazy='dynamic')`
- `calculate_price(variant_id=None)`: Computes base price + variant price.
- `gross_margin`: Sales price - Cost price.
- `margin_percentage`: Gross margin percentage.
- `to_dict(include_variants=True)`: JSON serializable representation.

---

### B. `ProductVariant` Model (`product_variants` table)
| Column Name | Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT AUTO_INCREMENT` | Primary Key | Unique variant identifier |
| `product_id` | `INT` | FOREIGN KEY (`products.id`), NOT NULL | Owning product |
| `name` | `VARCHAR(100)` | NOT NULL | Combined or display variant name |
| `variant_name` | `VARCHAR(50)` | NULLABLE | Variant attribute (e.g., `'Size'`, `'Tier'`, `'Edition'`) |
| `variant_value` | `VARCHAR(50)` | NULLABLE | Variant option (e.g., `'Large'`, `'Pro'`, `'Annual'`) |
| `sku` | `VARCHAR(64)` | UNIQUE, NOT NULL, Indexed | Variant-specific SKU |
| `price` | `DECIMAL(10, 2)` | NOT NULL, DEFAULT `0.00` | Direct price / additional price |
| `additional_price` | `DECIMAL(10, 2)` | NOT NULL, DEFAULT `0.00` | Additional variant price (in ? INR) |
| `attributes` | `JSON` | NULLABLE | Key-value attribute dictionary |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `True` | Active status |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Creation timestamp |

**Final Price Calculation Formula**:
$$\text{Final Price} = \text{Base Sales Price} + \text{Additional Variant Price}$$
*Example*: Product Base Price = ?2,000.00; Variant Additional Price = ?560.00; **Final Price = ?2,560.00**.

---

### C. `SubscriptionPlan` Model (`subscription_plans` table)
| Column Name | Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT AUTO_INCREMENT` | Primary Key, Indexed | Unique plan identifier |
| `product_id` | `INT` | FOREIGN KEY (`products.id`), NULLABLE | Optional linked base product |
| `name` | `VARCHAR(100)` | NOT NULL, Indexed | Plan name (e.g., `'Gold Monthly'`) |
| `code` | `VARCHAR(50)` | UNIQUE, NOT NULL, Indexed | Plan code (e.g., `'PLAN-GOLD-M'`) |
| `description`| `TEXT` | NULLABLE | Plan description / inclusions |
| `base_price` | `DECIMAL(10, 2)` | NOT NULL, DEFAULT `0.00` | Recurring price per interval (in ? INR), aliased as `price` |
| `billing_interval` | `VARCHAR(20)` | NOT NULL, DEFAULT `'monthly'` | Frequency: `'daily'`, `'weekly'`, `'monthly'`, `'quarterly'`, `'yearly'` |
| `interval_count` | `INT` | NOT NULL, DEFAULT `1` | Interval multiplier (e.g. every 1 month) |
| `trial_days` | `INT` | NOT NULL, DEFAULT `0` | Free trial period in days |
| `minimum_quantity` | `INT` | NOT NULL, DEFAULT `1` | Minimum units required for subscription |
| `start_date` | `DATE` | NOT NULL, DEFAULT `CURRENT_DATE` | Plan availability start date |
| `end_date` | `DATE` | NULLABLE | Plan availability expiration date (or NULL if ongoing) |
| `renewal_setting` | `VARCHAR(20)` | NOT NULL, DEFAULT `'automatic'` | Enum: `'automatic'`, `'manual'`, `'no-renewal'` |
| `closure_setting` | `VARCHAR(20)` | NOT NULL, DEFAULT `'at-period-end'` | Enum: `'at-period-end'`, `'immediate'` |
| `status` | `VARCHAR(20)` | NOT NULL, DEFAULT `'active'` | Enum: `'active'`, `'disabled'`, `'archived'` |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `True` | Active status flag |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` | Creation timestamp |
| `updated_at` | `DATETIME` | NOT NULL, ON UPDATE `CURRENT_TIMESTAMP` | Last updated timestamp |

**Lifecycle & Validation Rules**:
1. **Availability**: A plan is available on target date $D$ if and only if:
   $$\text{status} = \text{'active'} \quad \land \quad \text{start\_date} \le D \quad \land \quad ( \text{end\_date IS NULL} \lor D \le \text{end\_date} )$$
2. **Quantity Verification**: For any requested order quantity $Q$:
   $$Q \ge \text{minimum\_quantity}$$

---

## 3. Integration APIs for Teammates

### Sridhya (Quotations & Subscriptions):
- `GET /products/api/products?status=active`: Retrieve active products with their variants for quotation builder.
- `GET /products/api/products/<id>`: Full product details with nested variants.
- `GET /products/api/products/<id>/calculate-price?variant_id=<vid>`: Compute base + variant price.
- `GET /products/api/plans?status=active`: Retrieve all currently available plans.
- `GET /products/api/plans/<id>`: Retrieve plan details.
- `POST /products/api/plans/<id>/validate`: Validate whether a given quantity and order date can use this plan.

### Fairooz (Discounts):
- `GET /products/api/discountable`: Returns all active products with id, name, sku, and sales price for discount rules.
- `GET /products/api/products/<id>/pricing`: Returns sales price, cost price, and gross margin for discount ceiling checks.
