from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from models.user import User

def get_current_user():
    """Retrieves the currently active user from session, or a default admin in dev mode."""
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user
    
    # In development / demonstration mode, default to the seeded system administrator
    admin_user = User.query.filter_by(role='admin').first()
    return admin_user

def set_active_role(role_name):
    """Switches the session's active user by role for easy role-based access testing."""
    user = User.query.filter_by(role=role_name).first()
    if user:
        session['user_id'] = user.id
    return user

def admin_required(f):
    """Decorator to enforce Admin-only operations on backend routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin privileges required for this action.'}), 403
            flash('Access denied: You must be an administrator to create or manage discount rules.', 'danger')
            return redirect(url_for('discounts.list_discounts'))
        return f(*args, **kwargs)
    return decorated_function
