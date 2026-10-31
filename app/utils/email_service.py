import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

def generate_reset_token(user_id: int) -> str:
    """Generate a secure, time-limited password reset token for the given user ID."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    salt = current_app.config.get('PASSWORD_RESET_SALT', 'password-reset-salt-odoo-2026')
    return serializer.dumps({'user_id': user_id}, salt=salt)


def verify_reset_token(token: str) -> Optional[int]:
    """
    Verify the reset token.
    Returns user_id if valid, or None if invalid/expired.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    salt = current_app.config.get('PASSWORD_RESET_SALT', 'password-reset-salt-odoo-2026')
    timeout = current_app.config.get('PASSWORD_RESET_TIMEOUT', 3600)
    try:
        data = serializer.loads(token, salt=salt, max_age=timeout)
        return data.get('user_id')
    except (SignatureExpired, BadTimeSignature, Exception):
        return None


def send_password_reset_email(to_email: str, reset_url: str) -> Tuple[bool, str]:
    """
    Sends the password reset email if SMTP is configured.
    If SMTP settings are missing, logs the link securely and notifies caller
    without falsely claiming an email was sent.
    """
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_user = current_app.config.get('MAIL_USERNAME')
    mail_pwd = current_app.config.get('MAIL_PASSWORD')
    mail_port = current_app.config.get('MAIL_PORT', 587)
    use_tls = current_app.config.get('MAIL_USE_TLS', True)
    sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@subscription-odoo.com')

    # If SMTP is not configured, do not claim an email was delivered
    if not mail_server or not mail_user:
        current_app.logger.warning(
            f"[SMTP NOT CONFIGURED] Password reset requested for {to_email}. "
            f"Reset Link: {reset_url}"
        )
        return False, (
            "SMTP is not configured in .env. The password reset link has been logged to the server console for testing."
        )

    # Attempt to send via SMTP
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset Request - Subscription Management System'
        msg['From'] = sender
        msg['To'] = to_email

        text_content = (
            f"Hello,\n\n"
            f"A password reset was requested for your account. Please use the link below to set a new password:\n"
            f"{reset_url}\n\n"
            f"This link expires in 1 hour.\n"
            f"If you did not make this request, please disregard this email."
        )
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #714B67;">Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>A password reset was requested for your account on the Odoo Subscription Management Portal.</p>
                    <p style="margin: 24px 0;">
                        <a href="{reset_url}" style="background-color: #714B67; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Reset Your Password
                        </a>
                    </p>
                    <p>Or paste this link into your browser: <br><a href="{reset_url}">{reset_url}</a></p>
                    <p><small>This link is valid for 1 hour. If you did not make this request, you can safely ignore this email.</small></p>
                </div>
            </body>
        </html>
        """

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(mail_server, mail_port) as server:
            if use_tls:
                server.starttls()
            if mail_pwd:
                server.login(mail_user, mail_pwd)
            server.sendmail(sender, [to_email], msg.as_string())

        return True, "Password reset instructions have been sent to your email."
    except Exception as e:
        current_app.logger.error(f"Failed to deliver password reset email to {to_email}: {str(e)}")
        return False, f"Email delivery failed: {str(e)}. A local reset link is available in server logs."
