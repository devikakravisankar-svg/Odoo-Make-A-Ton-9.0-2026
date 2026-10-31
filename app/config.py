import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Base Configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'odoo-make-a-ton-secret-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MySQL Database Connection details
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_DB = os.getenv('MYSQL_DB', 'subscription_management_db')

    # Direct database URL override if specified
    DATABASE_URL = os.getenv('DATABASE_URL')

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Build MySQL PyMySQL connection string with safely quoted password
        encoded_password = quote_plus(MYSQL_PASSWORD) if MYSQL_PASSWORD else ''
        auth_part = f"{MYSQL_USER}:{encoded_password}@" if encoded_password else f"{MYSQL_USER}@"
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{auth_part}{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
        )

    # Email / SMTP Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@subscription-odoo.com')

    # Security Token Settings
    PASSWORD_RESET_SALT = 'password-reset-salt-odoo-2026'
    PASSWORD_RESET_TIMEOUT = 3600  # 1 hour in seconds


class DevelopmentConfig(Config):
    """Development Configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing Configuration (Uses in-memory SQLite for isolated test runs)."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production Configuration."""
    DEBUG = False
    TESTING = False


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
