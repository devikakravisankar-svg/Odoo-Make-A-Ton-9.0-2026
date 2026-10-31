// Client-side interactions for Products and Subscription Plans (Nidha's Module)
document.addEventListener('DOMContentLoaded', () => {
  // Auto-uppercase for product & plan code inputs
  const codeInputs = document.querySelectorAll('input[name="code"], input[name="sku"]');
  codeInputs.forEach(input => {
    input.addEventListener('input', (e) => {
      e.target.value = e.target.value.toUpperCase();
    });
  });

  // Quick API calculator helper if used on quotes/subs pages
  window.calculateProductPrice = async function(productId, variantId) {
    let url = `/products/api/products/${productId}/calculate-price`;
    if (variantId) {
      url += `?variant_id=${variantId}`;
    }
    try {
      const resp = await fetch(url);
      return await resp.json();
    } catch (e) {
      console.error("Error calculating product price:", e);
      return null;
    }
  };

  // Quick plan validator helper for Sridhya
  window.validateSubscriptionPlan = async function(planId, quantity, orderDate) {
    try {
      const resp = await fetch(`/products/api/plans/${planId}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: quantity, date: orderDate })
      });
      return await resp.json();
    } catch (e) {
      console.error("Error validating plan:", e);
      return { valid: false, errors: ['Network error'] };
    }
  };
});
