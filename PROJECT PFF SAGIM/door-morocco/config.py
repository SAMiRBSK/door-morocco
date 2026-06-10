"""
Door Morocco — Application Configuration
==========================================
All sensitive values are loaded from environment variables.
Copy `.env.example` → `.env` and fill in your credentials.
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG = False
    TESTING = False

    # MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "doormorocco")

    # Uploads
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "static", "uploads"
    )
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024           # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Flask-Mail (Gmail SMTP)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")          # your-email@gmail.com
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")          # Gmail App Password
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "Door Morocco <noreply@doormorocco.com>")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@doormorocco.com")


class DevelopmentConfig(Config):
    """Development overrides."""
    DEBUG = True


class ProductionConfig(Config):
    """Production hardening."""
    DEBUG = False


# Quick lookup
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
