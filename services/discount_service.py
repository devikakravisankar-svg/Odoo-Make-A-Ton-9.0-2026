from datetime import datetime, date
from decimal import Decimal
from extensions import db
from models.discount import Discount
from models.invoice import Invoice
from models.invoice_discount import InvoiceDiscount
from models.invoice_line import InvoiceLine

class DiscountValidationError(Exception):
    """Custom exception raised for invalid discount operations."""
    pass

class DiscountService:

    @staticmethod
    def create_discount(data, current_user=None):
        """
        Creates a new discount rule. Restricts creation to Admin.
        """
        if current_user and not current_user.is_admin():
            raise DiscountValidationError("Access Denied: Only Admin users can create discount rules.")

        name = data.get('name', '').strip()
        if not name:
            raise DiscountValidationError("Discount name is required.")

        discount_type = data.get('discount_type', 'fixed')
        if discount_type not in ('fixed', 'percentage'):
            raise DiscountValidationError("Invalid discount type. Must be 'fixed' or 'percentage'.")

        try:
            discount_value = Decimal(str(data.get('discount_value', 0)))
            if discount_value <= Decimal('0.00'):
                raise DiscountValidationError("Discount value must be greater than zero.")
            if discount_type == 'percentage' and discount_value > Decimal('100.00'):
                raise DiscountValidationError("Percentage discount cannot exceed 100%.")
        except (ValueError, TypeError):
            raise DiscountValidationError("Invalid discount value format.")

        try:
            min_purchase = Decimal(str(data.get('min_purchase_amount', 0.00)))
            if min_purchase < Decimal('0.00'):
                raise DiscountValidationError("Minimum purchase amount cannot be negative.")
        except (ValueError, TypeError):
            min_purchase = Decimal('0.00')

        min_quantity = int(data.get('min_quantity', 0))
        if min_quantity < 0:
            raise DiscountValidationError("Minimum quantity cannot be negative.")

        # Date validations
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not start_date or not end_date:
            raise DiscountValidationError("Start date and end date are both required.")

        if start_date > end_date:
            raise DiscountValidationError("Start date cannot be after the end date.")

        max_usage = data.get('max_usage_limit')
        if max_usage is not None and str(max_usage).strip() != '':
            max_usage = int(max_usage)
            if max_usage <= 0:
                raise DiscountValidationError("Maximum usage limit must be at least 1.")
        else:
            max_usage = None

        scope = data.get('scope', 'subscription')
        if scope not in ('product', 'subscription'):
            raise DiscountValidationError("Scope must be 'product' or 'subscription'.")

        applicable_product_id = data.get('applicable_product_id')
        if scope == 'product' and not applicable_product_id:
            raise DiscountValidationError("Product-specific discounts require an applicable product.")

        discount = Discount(
            name=name,
            code=data.get('code', '').strip().upper() or None,
            discount_type=discount_type,
            discount_value=discount_value,
            min_purchase_amount=min_purchase,
            min_quantity=min_quantity,
            start_date=start_date,
            end_date=end_date,
            max_usage_limit=max_usage,
            current_usage_count=0,
            scope=scope,
            applicable_product_id=int(applicable_product_id) if (scope == 'product' and applicable_product_id) else None,
            is_active=bool(data.get('is_active', True))
        )

        db.session.add(discount)
        db.session.commit()
        return discount

    @staticmethod
    def update_discount(discount_id, data, current_user=None):
        """
        Updates an existing discount rule. Restricts update to Admin.
        """
        if current_user and not current_user.is_admin():
            raise DiscountValidationError("Access Denied: Only Admin users can modify discount rules.")

        discount = Discount.query.get(discount_id)
        if not discount:
            raise DiscountValidationError(f"Discount #{discount_id} not found.")

        if 'name' in data and data['name'].strip():
            discount.name = data['name'].strip()

        if 'code' in data:
            discount.code = data['code'].strip().upper() or None

        if 'discount_type' in data:
            if data['discount_type'] in ('fixed', 'percentage'):
                discount.discount_type = data['discount_type']

        if 'discount_value' in data:
            val = Decimal(str(data['discount_value']))
            if val <= Decimal('0.00'):
                raise DiscountValidationError("Discount value must be greater than zero.")
            if discount.discount_type == 'percentage' and val > Decimal('100.00'):
                raise DiscountValidationError("Percentage discount cannot exceed 100%.")
            discount.discount_value = val

        if 'min_purchase_amount' in data:
            discount.min_purchase_amount = Decimal(str(data['min_purchase_amount']))

        if 'min_quantity' in data:
            discount.min_quantity = int(data['min_quantity'])

        if 'start_date' in data and data['start_date']:
            d = data['start_date']
            discount.start_date = datetime.strptime(d, '%Y-%m-%d').date() if isinstance(d, str) else d

        if 'end_date' in data and data['end_date']:
            d = data['end_date']
            discount.end_date = datetime.strptime(d, '%Y-%m-%d').date() if isinstance(d, str) else d

        if discount.start_date > discount.end_date:
            raise DiscountValidationError("Start date cannot be after end date.")

        if 'max_usage_limit' in data:
            limit = data['max_usage_limit']
            discount.max_usage_limit = int(limit) if (limit is not None and str(limit).strip() != '') else None

        if 'is_active' in data:
            discount.is_active = bool(data['is_active'])

        db.session.commit()
        return discount

    @staticmethod
    def toggle_status(discount_id, current_user=None):
        """Enables or disables a discount rule (Admin only)."""
        if current_user and not current_user.is_admin():
            raise DiscountValidationError("Access Denied: Only Admin can toggle discount status.")

        discount = Discount.query.get(discount_id)
        if not discount:
            raise DiscountValidationError("Discount not found.")

        discount.is_active = not discount.is_active
        db.session.commit()
        return discount

    @staticmethod
    def get_eligible_discounts_for_invoice(invoice):
        """
        Returns all discounts currently eligible for a given invoice:
        - Active rule
        - Within valid date window (start_date <= invoice_date <= end_date)
        - Not exceeded max usage limit
        - Satisfies min purchase amount & min line quantity
        - Scope matches (subscription-wide, or matching product exists on invoice)
        - Not already applied to this invoice
        """
        all_discounts = Discount.query.filter_by(is_active=True).all()
        already_applied_ids = {ad.discount_id for ad in invoice.applied_discounts}
        
        eligible = []
        for d in all_discounts:
            if d.id in already_applied_ids:
                continue
            
            # Check eligibility
            if d.scope == 'product':
                matching_lines = [l for l in invoice.lines if l.product_id == d.applicable_product_id]
                if not matching_lines:
                    continue
                prod_subtotal = sum((l.subtotal for l in matching_lines), Decimal('0.00'))
                prod_qty = sum((l.quantity for l in matching_lines), 0)
                is_valid, _ = d.validate_eligibility(prod_subtotal, prod_qty, d.applicable_product_id, invoice.invoice_date)
            else:
                total_qty = sum((l.quantity for l in invoice.lines), 0)
                is_valid, _ = d.validate_eligibility(invoice.subtotal, total_qty, reference_date=invoice.invoice_date)
            
            if is_valid:
                eligible.append(d)
        return eligible

    @staticmethod
    def apply_automatic_discounts_to_invoice(invoice):
        """
        Automatically finds and applies all eligible auto-apply discounts
        (e.g., promo rules with no code or global rules) to an invoice.
        Stops once expired, exhausted, or when subtotal reaches zero.
        """
        eligible = DiscountService.get_eligible_discounts_for_invoice(invoice)
        applied_results = []
        for disc in eligible:
            # Auto-applied rules: rules without a specific promo code or marked automatic
            if not disc.code or disc.code.startswith('AUTO'):
                try:
                    invoice, deduction = DiscountService.apply_discount_to_invoice(invoice, disc)
                    applied_results.append((disc, deduction))
                except DiscountValidationError:
                    continue
        return invoice, applied_results

    @staticmethod
    def apply_discount_to_invoice(invoice, discount):
        """
        Applies a discount to an invoice:
        - Validates active status, date range, minimum conditions, and quota limits
        - Prevents duplicate applications of the same discount
        - Computes product-specific or subscription-wide deduction
        - Ensures final invoice total NEVER drops below zero
        - Increments discount usage count
        - Audits application in InvoiceDiscount table
        """
        if not discount:
            raise DiscountValidationError("No discount specified.")

        # 1. Prevent duplicate discount application
        existing = InvoiceDiscount.query.filter_by(invoice_id=invoice.id, discount_id=discount.id).first()
        if existing:
            raise DiscountValidationError(f"Discount '{discount.name}' is already applied to this invoice.")

        # 2. Check scope and eligibility
        if discount.scope == 'product':
            # Find matching product line
            matching_lines = [l for l in invoice.lines if l.product_id == discount.applicable_product_id]
            if not matching_lines:
                raise DiscountValidationError(
                    f"Discount '{discount.name}' applies only to product ID {discount.applicable_product_id}, which is not on this invoice."
                )
            
            product_subtotal = sum((l.subtotal for l in matching_lines), Decimal('0.00'))
            product_qty = sum((l.quantity for l in matching_lines), 0)
            
            is_valid, reason = discount.validate_eligibility(
                subtotal=product_subtotal,
                quantity=product_qty,
                product_id=discount.applicable_product_id,
                reference_date=invoice.invoice_date
            )
            if not is_valid:
                raise DiscountValidationError(f"Discount ineligible: {reason}")
            
            # Calculate discount on matching line total
            deduction = discount.calculate_discount_amount(product_subtotal)
        else:
            # Subscription-wide scope
            total_qty = sum((l.quantity for l in invoice.lines), 0)
            is_valid, reason = discount.validate_eligibility(
                subtotal=invoice.subtotal,
                quantity=total_qty,
                reference_date=invoice.invoice_date
            )
            if not is_valid:
                raise DiscountValidationError(f"Discount ineligible: {reason}")

            # Calculate discount on invoice subtotal
            deduction = discount.calculate_discount_amount(invoice.subtotal)

        if deduction <= Decimal('0.00'):
            raise DiscountValidationError("Calculated discount amount is zero.")

        # 3. Ensure invoice total never drops below zero
        current_discount = invoice.discount_amount or Decimal('0.00')
        max_allowed_discount = invoice.subtotal or Decimal('0.00')
        
        new_total_discount = min(current_discount + deduction, max_allowed_discount)
        actual_deduction = new_total_discount - current_discount

        if actual_deduction <= Decimal('0.00'):
            raise DiscountValidationError("Discount cannot be applied as invoice subtotal is already fully discounted.")

        # 4. Record application in audit table
        audit = InvoiceDiscount(
            invoice_id=invoice.id,
            discount_id=discount.id,
            applied_amount=actual_deduction
        )
        db.session.add(audit)

        # 5. Increment usage count
        discount.current_usage_count += 1

        # 6. Recalculate invoice totals
        invoice.discount_amount = new_total_discount
        taxable_base = max(Decimal('0.00'), invoice.subtotal - invoice.discount_amount)
        # Total cannot be negative
        invoice.total_amount = max(Decimal('0.00'), taxable_base + invoice.tax_amount)
        
        # 7. Refresh invoice payment status
        invoice.refresh_payment_status()

        db.session.commit()
        return invoice, actual_deduction
