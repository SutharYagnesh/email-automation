import os
from flask import Flask
from config import Config

def create_app():
    """Simple Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.contacts import contacts_bp
    from app.routes.senders import senders_bp
    from app.routes.templates import templates_bp
    from app.routes.campaigns import campaigns_bp
    from app.routes.tracking import tracking_bp
    from app.routes.settings import settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(senders_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(settings_bp)
    
    # Safe date formatting filter for templates
    @app.template_filter('datetime_format')
    def datetime_format(val, fmt='%b %d, %Y %H:%M'):
        if not val:
            return '-'
        if hasattr(val, 'strftime'):
            return val.strftime(fmt)
        return str(val)
        
    return app
