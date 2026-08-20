from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.routes.auth import login_required
from app.services.sender_service import (
    create_sender_account, update_sender_account, delete_sender_account,
    get_sender_accounts, test_sender_connection, check_domain_deliverability
)

senders_bp = Blueprint("senders", __name__)

@senders_bp.route("/senders")
@login_required
def index():
    user_id = session.get("user_id")
    senders = get_sender_accounts(user_id)
    return render_template("senders/index.html", senders=senders)

@senders_bp.route("/senders/add", methods=["POST"])
@login_required
def add():
    user_id = session.get("user_id")
    username = request.form.get("username", "")
    app_password = request.form.get("app_password", "")
    sender_name = request.form.get("sender_name", "")
    reply_to = request.form.get("reply_to", "")
    smtp_port = int(request.form.get("smtp_port", 465))
    
    success, message, sender = create_sender_account(
        user_id=user_id,
        username=username,
        app_password=app_password,
        sender_name=sender_name,
        reply_to=reply_to,
        smtp_port=smtp_port
    )
    
    if success:
        flash(message, "success")
        # Automatically trigger initial connection test
        test_sender_connection(sender["_id"], user_id)
    else:
        flash(message, "danger")
        
    return redirect(url_for("senders.index"))

@senders_bp.route("/senders/<sender_id>/edit", methods=["POST"])
@login_required
def edit(sender_id):
    user_id = session.get("user_id")
    data = {
        "sender_name": request.form.get("sender_name", ""),
        "reply_to": request.form.get("reply_to", ""),
        "smtp_port": int(request.form.get("smtp_port", 465))
    }
    if request.form.get("app_password"):
        data["app_password"] = request.form.get("app_password")
        
    success, message = update_sender_account(sender_id, user_id, data)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("senders.index"))

@senders_bp.route("/senders/<sender_id>/delete", methods=["POST"])
@login_required
def delete(sender_id):
    user_id = session.get("user_id")
    success, message = delete_sender_account(sender_id, user_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("senders.index"))

@senders_bp.route("/senders/<sender_id>/test", methods=["POST"])
@login_required
def test_connection(sender_id):
    user_id = session.get("user_id")
    success, message = test_sender_connection(sender_id, user_id)
    return jsonify({"success": success, "message": message})

@senders_bp.route("/senders/check-domain", methods=["POST"])
@login_required
def check_domain():
    domain = request.json.get("domain", "") if request.is_json else request.form.get("domain", "")
    if not domain:
        return jsonify({"success": False, "message": "Domain is required."}), 400
    results = check_domain_deliverability(domain)
    return jsonify({"success": True, "results": results})
