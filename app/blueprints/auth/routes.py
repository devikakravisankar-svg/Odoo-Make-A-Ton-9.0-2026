from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.utils.validators import validate_password_strength
from app.utils.email_service import generate_reset_token, verify_reset_token, send_password_reset_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration endpoint."""
    if current_user.is_authenticated:
        if current_user.is_admin_or_staff:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('portal.index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic presence validation
        if not full_name or not username or not email or not password:
            flash("All required fields must be filled out.", "danger")
            return render_template('auth/register.html', full_name=full_name, username=username, email=email, phone=phone)

        # Confirm password match
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register.html', full_name=full_name, username=username, email=email, phone=phone)

        # Strong password validation (>8 chars, uppercase, lowercase, special char)
        is_strong, msg = validate_password_strength(password)
        if not is_strong:
            flash(msg, "danger")
            return render_template('auth/register.html', full_name=full_name, username=username, email=email, phone=phone)

        # Check existing username or email
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.", "warning")
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone)

        if User.query.filter_by(email=email).first():
            flash("An account with this email address already exists.", "warning")
            return render_template('auth/register.html', full_name=full_name, username=username, phone=phone)

        # Create new customer user
        new_customer = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone if phone else None,
            role=User.ROLE_CUSTOMER,
            is_active=True
        )
        new_customer.set_password(password)

        db.session.add(new_customer)
        db.session.commit()

        flash("Registration successful! You may now sign in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint for Customer, Staff, and Admin."""
    if current_user.is_authenticated:
        if current_user.is_admin_or_staff:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('portal.index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()  # Can be username or email
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_id or not password:
            flash("Please enter both username/email and password.", "warning")
            return render_template('auth/login.html')

        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id.lower())
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid credentials. Please verify your details.", "danger")
            return render_template('auth/login.html', login_id=login_id)

        if not user.is_active:
            flash("This account has been deactivated. Please contact support.", "danger")
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.full_name}!", "success")

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        if user.is_admin_or_staff:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('portal.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout endpoint."""
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request workflow."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_reset_token(user.id)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            sent, status_msg = send_password_reset_email(user.email, reset_url)

            if sent:
                flash(status_msg, "success")
            else:
                # Disclosed responsibly when SMTP is unconfigured for local development/testing
                flash(status_msg, "info")
                flash(f"Direct reset link for testing: {reset_url}", "warning")
        else:
            # Prevent email enumeration while maintaining user feedback
            flash("If an account exists with that email address, reset instructions have been generated.", "info")

        return redirect(url_for('auth.login'))

    return render_template('auth/request_reset.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset completion with token verification."""
    user_id = verify_reset_token(token)
    if not user_id:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth.forgot_password'))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/reset_password.html', token=token)

        is_strong, msg = validate_password_strength(password)
        if not is_strong:
            flash(msg, "danger")
            return render_template('auth/reset_password.html', token=token)

        user.set_password(password)
        db.session.commit()

        flash("Your password has been successfully reset! Please sign in with your new password.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
