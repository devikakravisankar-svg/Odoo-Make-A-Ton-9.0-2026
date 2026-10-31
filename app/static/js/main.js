// Client-side interactions for Odoo Subscription Management System
document.addEventListener('DOMContentLoaded', () => {
  // Live Password Validator for registration and reset screens
  const passwordInput = document.getElementById('password-input');
  const reqLength = document.getElementById('req-length');
  const reqUpper = document.getElementById('req-upper');
  const reqLower = document.getElementById('req-lower');
  const reqSpecial = document.getElementById('req-special');

  if (passwordInput && reqLength && reqUpper && reqLower && reqSpecial) {
    const specialCharRegex = /[^a-zA-Z0-9]/;

    passwordInput.addEventListener('input', () => {
      const val = passwordInput.value;

      // > 8 characters
      if (val.length > 8) {
        reqLength.style.color = '#16a34a';
        reqLength.textContent = '✓ More than 8 characters';
      } else {
        reqLength.style.color = '#dc2626';
        reqLength.textContent = '✗ More than 8 characters';
      }

      // Uppercase
      if (/[A-Z]/.test(val)) {
        reqUpper.style.color = '#16a34a';
        reqUpper.textContent = '✓ At least one uppercase letter';
      } else {
        reqUpper.style.color = '#dc2626';
        reqUpper.textContent = '✗ At least one uppercase letter';
      }

      // Lowercase
      if (/[a-z]/.test(val)) {
        reqLower.style.color = '#16a34a';
        reqLower.textContent = '✓ At least one lowercase letter';
      } else {
        reqLower.style.color = '#dc2626';
        reqLower.textContent = '✗ At least one lowercase letter';
      }

      // Special character
      if (specialCharRegex.test(val)) {
        reqSpecial.style.color = '#16a34a';
        reqSpecial.textContent = '✓ At least one special character (!@#$%^&*)';
      } else {
        reqSpecial.style.color = '#dc2626';
        reqSpecial.textContent = '✗ At least one special character (!@#$%^&*)';
      }
    });
  }

  // Dismiss alert buttons
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.target.closest('.alert').remove();
    });
  });
});
