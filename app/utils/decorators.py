from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """Decorator ensuring that only Admin users can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash("Access denied: Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    """Decorator ensuring that Admin or Internal Staff users can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin_or_staff:
            flash("Access denied: Staff or Administrator privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def customer_required(f):
    """Decorator ensuring that Customer users (or Admins for previewing) can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        # If an internal user accesses portal, allow them to view, but customers cannot access admin/staff routes
        return f(*args, **kwargs)
    return decorated_function
