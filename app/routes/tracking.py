from flask import Blueprint, render_template, request
from app.services.tracking_service import record_email_open, process_unsubscribe

tracking_bp = Blueprint("tracking", __name__)

@tracking_bp.route("/track/open/<tracking_id>")
def track_open(tracking_id):
    """Public open tracking pixel endpoint."""
    return record_email_open(tracking_id)

@tracking_bp.route("/unsubscribe/<tracking_id>")
def unsubscribe(tracking_id):
    """Public unsubscribe page endpoint."""
    success, message, recipient_email = process_unsubscribe(tracking_id)
    return render_template("tracking/unsubscribed.html", success=success, message=message, email=recipient_email)
