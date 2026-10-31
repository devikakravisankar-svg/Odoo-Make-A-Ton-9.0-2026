// Brightloop Billing Management - Vanilla JavaScript (Member 4)

document.addEventListener('DOMContentLoaded', function () {
    // 1. Dynamic Discount Scope Handler
    const scopeSelect = document.getElementById('discount-scope-select');
    const productFieldGroup = document.getElementById('product-selector-group');

    if (scopeSelect && productFieldGroup) {
        function toggleProductField() {
            if (scopeSelect.value === 'product') {
                productFieldGroup.style.display = 'block';
                const productSelect = productFieldGroup.querySelector('select');
                if (productSelect) productSelect.required = true;
            } else {
                productFieldGroup.style.display = 'none';
                const productSelect = productFieldGroup.querySelector('select');
                if (productSelect) {
                    productSelect.required = false;
                    productSelect.value = '';
                }
            }
        }
        scopeSelect.addEventListener('change', toggleProductField);
        toggleProductField(); // run on initial page load
    }

    // 2. Dynamic Payment Form - Real-time Invoice Balance Lookup & Overpayment Guard
    const invoiceSelect = document.getElementById('payment-invoice-select');
    const amountInput = document.getElementById('payment-amount-input');
    const balanceBox = document.getElementById('invoice-balance-details');
    const overpaymentWarning = document.getElementById('overpayment-warning');

    if (invoiceSelect && amountInput) {
        let currentOutstanding = 0.0;

        function fetchInvoiceDetails(invoiceId) {
            if (!invoiceId) {
                if (balanceBox) balanceBox.style.display = 'none';
                currentOutstanding = 0.0;
                return;
            }

            fetch(`/payments/api/invoice/${invoiceId}/balance`)
                .then(response => {
                    if (!response.ok) throw new Error('Invoice details could not be loaded.');
                    return response.json();
                })
                .then(data => {
                    currentOutstanding = parseFloat(data.outstanding_amount);

                    // Update UI elements
                    const custElem = document.getElementById('detail-customer');
                    const totalElem = document.getElementById('detail-total');
                    const paidElem = document.getElementById('detail-paid');
                    const outstandingElem = document.getElementById('detail-outstanding');
                    const dueElem = document.getElementById('detail-due');

                    if (custElem) custElem.textContent = data.customer_name;
                    if (totalElem) totalElem.textContent = `$${data.total_amount.toFixed(2)}`;
                    if (paidElem) paidElem.textContent = `$${data.total_paid.toFixed(2)}`;
                    if (outstandingElem) outstandingElem.textContent = `$${data.outstanding_amount.toFixed(2)}`;
                    if (dueElem) dueElem.textContent = data.due_date;

                    // Set amount suggestion if empty
                    if (!amountInput.value || parseFloat(amountInput.value) <= 0) {
                        amountInput.value = data.outstanding_amount.toFixed(2);
                    }

                    if (balanceBox) balanceBox.style.display = 'block';
                    validateAmountAgainstBalance();
                })
                .catch(err => {
                    console.error('Error fetching invoice balance:', err);
                });
        }

        function validateAmountAgainstBalance() {
            const enteredAmount = parseFloat(amountInput.value);
            if (!isNaN(enteredAmount) && currentOutstanding > 0) {
                if (enteredAmount > currentOutstanding + 0.001) {
                    if (overpaymentWarning) {
                        overpaymentWarning.style.display = 'block';
                        overpaymentWarning.textContent = `⚠ Overpayment blocked: Amount ($${enteredAmount.toFixed(2)}) exceeds outstanding balance ($${currentOutstanding.toFixed(2)}).`;
                    }
                    amountInput.setCustomValidity('Payment amount exceeds outstanding balance.');
                } else if (enteredAmount <= 0) {
                    if (overpaymentWarning) {
                        overpaymentWarning.style.display = 'block';
                        overpaymentWarning.textContent = `⚠ Payment amount must be greater than zero.`;
                    }
                    amountInput.setCustomValidity('Payment must be > $0.00.');
                } else {
                    if (overpaymentWarning) overpaymentWarning.style.display = 'none';
                    amountInput.setCustomValidity('');
                }
            } else {
                if (overpaymentWarning) overpaymentWarning.style.display = 'none';
                amountInput.setCustomValidity('');
            }
        }

        invoiceSelect.addEventListener('change', function () {
            fetchInvoiceDetails(this.value);
        });

        amountInput.addEventListener('input', validateAmountAgainstBalance);

        // Run if an invoice is already selected on page load (e.g. from query param)
        if (invoiceSelect.value) {
            fetchInvoiceDetails(invoiceSelect.value);
        }
    }
});
