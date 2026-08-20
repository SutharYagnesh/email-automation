import os
from flask import Flask
from config import Config
from app.db import init_db
from app.services.reply_monitor_service import start_background_reply_monitor

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Create upload directory
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Initialize MongoDB connection & indexes
    init_db(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.contacts import contacts_bp
    from app.routes.groups import groups_bp
    from app.routes.senders import senders_bp
    from app.routes.templates import templates_bp
    from app.routes.campaigns import campaigns_bp
    from app.routes.tracking import tracking_bp
    from app.routes.settings import settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(senders_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(settings_bp)
    
    # Start background IMAP reply monitor
    try:
        start_background_reply_monitor(interval_seconds=120)
    except Exception as e:
        print(f"[App Init Warning] Could not start reply monitor: {e}")
        
    return app
