import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    JWT_SECRET_KEY = (
        os.environ.get("JWT_SECRET_KEY") or "jwt-secret-key-change-in-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///it_ops.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    CORS_HEADERS = "Content-Type"
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]

    PAGE_DEFAULT_SIZE = 20
    PAGE_MAX_SIZE = 100

    # SocketIO configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
    SOCKETIO_ASYNC_MODE = "threading"

    # Notification settings
    NOTIFICATION_RETENTION_DAYS = 90
    NOTIFICATION_MAX_RETRY_ATTEMPTS = 3
    NOTIFICATION_RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ECHO = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
