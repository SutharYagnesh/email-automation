import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-flask-secret-key-change-me")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://karanzala9789_db_user:5yFJeYDI3dxDmnGh@ac-5hmq1fu-shard-00-00.opfleab.mongodb.net:27017,ac-5hmq1fu-shard-00-01.opfleab.mongodb.net:27017,ac-5hmq1fu-shard-00-02.opfleab.mongodb.net:27017/?ssl=true&replicaSet=atlas-u5eria-shard-0&authSource=admin&appName=Cluster0")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "email_automation")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "W9LwY2Vd9U1Xq6s8t2Z5a8B0c3D6e9F2g5H8j1K4m7N=")
    
    # App URL for tracking pixel & unsubscribe link generation
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")
    
    # File upload configurations
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload limit
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "pdf", "doc", "docx", "png", "jpg", "jpeg", "txt"}
    
    # Session config
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production HTTPS
    
    # Email throttling defaults
    DEFAULT_DELAY_BETWEEN_EMAILS = 2.0  # seconds
    DEFAULT_MAX_BATCH_SIZE = 50
