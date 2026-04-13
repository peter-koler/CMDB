import os
from datetime import timedelta
import redis


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    JWT_SECRET_KEY = (
        os.environ.get("JWT_SECRET_KEY") or "jwt-secret-key-change-in-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    CORS_HEADERS = "Content-Type"
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
    
    # Session configuration - Redis
    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.from_url(
        os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    )
    SESSION_KEY_PREFIX = "itops:session:"
    SESSION_USE_SIGNER = False  # Werkzeug 3.0 兼容性
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Cookie security
    SESSION_COOKIE_NAME = "session_id"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True

    PAGE_DEFAULT_SIZE = 20
    PAGE_MAX_SIZE = 100
    CMDB_TOPOLOGY_MAX_DEPTH = int(os.environ.get("CMDB_TOPOLOGY_MAX_DEPTH", "10"))

    # SocketIO configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
    SOCKETIO_ASYNC_MODE = "threading"

    # Notification settings
    NOTIFICATION_RETENTION_DAYS = 90
    NOTIFICATION_MAX_RETRY_ATTEMPTS = 3
    NOTIFICATION_RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min

    # Go Manager API integration
    GO_MANAGER_URL = os.environ.get("GO_MANAGER_URL", "http://127.0.0.1:8080")
    GO_MANAGER_TIMEOUT_SECONDS = float(os.environ.get("GO_MANAGER_TIMEOUT_SECONDS", "3"))
    GO_MANAGER_MAX_RETRIES = int(os.environ.get("GO_MANAGER_MAX_RETRIES", "2"))
    GO_MANAGER_CB_FAILURE_THRESHOLD = int(os.environ.get("GO_MANAGER_CB_FAILURE_THRESHOLD", "3"))
    GO_MANAGER_CB_RECOVERY_SECONDS = int(os.environ.get("GO_MANAGER_CB_RECOVERY_SECONDS", "30"))
    GO_MANAGER_USE_SYSTEM_PROXY = os.environ.get("GO_MANAGER_USE_SYSTEM_PROXY", "false")


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
