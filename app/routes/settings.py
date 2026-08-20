from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.routes.auth import login_required
from app.services.reply_monitor_service import check_sender_replies
from app.services.sender_service import get_sender_accounts
from app.db import get_db
from bson import ObjectId

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings")
@login_required
def index():
    user_id = session.get("user_id")
    senders = get_sender_accounts(user_id)
    return render_template("settings/index.html", senders=senders)

@settings_bp.route("/settings/check-replies", methods=["POST"])
@login_required
def manual_check_replies():
    user_id = session.get("user_id")
    sender_id = request.form.get("sender_id") or request.json.get("sender_id") if request.is_json else None
    
    senders = get_sender_accounts(user_id) if not sender_id else [{"_id": sender_id}]
    total_replies = 0
    for s in senders:
        count = check_sender_replies(s["_id"], user_id)
        total_replies += count
        
    msg = f"Reply scan completed! {total_replies} new replies detected."
    if request.is_json:
        return jsonify({"success": True, "message": msg, "replies_found": total_replies})
        
    flash(msg, "success")
    return redirect(url_for("settings.index"))
