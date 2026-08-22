import os
from flask import Flask
from config import Config

def datetime_format(val, fmt='%b %d, %Y %H:%M'):
    """Safe date formatting Jinja filter."""
    if not val:
        return '-'
    if hasattr(val, 'strftime'):
        return val.strftime(fmt)
    try:
        from datetime import datetime
        if isinstance(val, str):
            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
            return dt.strftime(fmt)
    except Exception:
        pass
    return str(val)

def create_app():
    """Simple Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Register Jinja custom filters directly
    app.jinja_env.filters['datetime_format'] = datetime_format
    app.template_filter('datetime_format')(datetime_format)
    
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
    
    # 413 Request Entity Too Large error handler
    @app.errorhandler(413)
    def request_entity_too_large(error):
        from flask import flash, redirect, request, url_for
        flash("File upload size is too large. Please upload files smaller than 10 MB.", "danger")
        return redirect(request.referrer or url_for('dashboard.index'))

    return app
