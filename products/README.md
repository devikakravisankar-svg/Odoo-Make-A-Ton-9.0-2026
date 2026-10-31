# Product Management & Subscription Plans Module

**Assigned Member:** Nidha  
**Blueprint Name:** `products_bp`  
**URL Prefix:** `/products`

## Models in Scope
- `Product` (`app/models/product.py`)
  - Fields: `id`, `name`, `code`, `description`, `base_price`, `is_active`, `created_at`
- `ProductVariant` (`app/models/product.py`)
  - Fields: `id`, `product_id`, `name`, `sku`, `price`, `attributes` (JSON), `is_active`, `created_at`
- `SubscriptionPlan` (`app/models/plan.py`)
  - Fields: `id`, `name`, `code`, `description`, `billing_interval`, `interval_count`, `base_price`, `trial_days`, `is_active`, `created_at`

## Module Responsibilities
1. Product CRUD operations (create, view, update, toggle active status).
2. Product Variants management (add variants, set SKUs and pricing).
3. Subscription Plans CRUD (define intervals: monthly/yearly, trial periods, pricing).
4. Staff / Admin access control using `@staff_required`.

## Note for Nidha
Please keep your routes inside `routes.py` in this folder or in sub-controllers inside this directory. Do not modify core authentication or foundation files.
