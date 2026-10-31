import os
import socket
from dotenv import load_dotenv

load_dotenv()

def is_mysql_available(host='localhost', port=3306):
    """Checks if MySQL service is listening on the target host/port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8)
        res = s.connect_ex((host, int(port)))
        s.close()
        return res == 0
    except Exception:
        return False

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'brightloop-super-secret-key-2026')
    
    # MySQL Database Configuration (Primary for Hackathon / Production)
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_DB = os.getenv('MYSQL_DB', 'subscription_db')
    
    mysql_uri = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

    # If MySQL service is running, use MySQL. If stopped, use SQLite dev fallback so app runs immediately.
    if is_mysql_available(MYSQL_HOST, MYSQL_PORT):
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', mysql_uri)
        DB_ENGINE = 'MySQL'
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///subscription_db.db')
        DB_ENGINE = 'SQLite (Dev Fallback - Start XAMPP MySQL for MySQL mode)'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
