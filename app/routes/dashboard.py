from flask import Blueprint, render_template, session, jsonify
from app.db import get_db
from app.routes.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    user_id = session.get("user_id")
    db = get_db()
    
    # 1. Total Metrics Counts
    total_contacts = db.contacts.count_documents({"user_id": user_id})
    total_groups = db.groups.count_documents({"user_id": user_id})
    total_campaigns = db.campaigns.count_documents({"user_id": user_id})
    total_emails_sent = db.sent_emails.count_documents({"user_id": user_id})
    
    # Email Delivery Breakdown
    sent_count = db.sent_emails.count_documents({"user_id": user_id, "status": "sent"})
    delivered_count = db.sent_emails.count_documents({"user_id": user_id, "status": {"$in": ["delivered", "opened", "replied"]}})
    opened_count = db.sent_emails.count_documents({"user_id": user_id, "status": {"$in": ["opened", "replied"]}})
    replied_count = db.sent_emails.count_documents({"user_id": user_id, "status": "replied"})
    failed_count = db.sent_emails.count_documents({"user_id": user_id, "status": "failed"})
    
    not_opened_count = max(0, delivered_count - opened_count)
    
    # Rates
    open_rate = round((opened_count / delivered_count * 100), 1) if delivered_count > 0 else 0.0
    reply_rate = round((replied_count / delivered_count * 100), 1) if delivered_count > 0 else 0.0
    
    # Recent Campaigns Overview List
    recent_campaigns = list(db.campaigns.find({"user_id": user_id}).sort("created_at", -1).limit(5))
    for c in recent_campaigns:
        c["_id"] = str(c["_id"])
        
    stats = {
        "total_contacts": total_contacts,
        "total_groups": total_groups,
        "total_campaigns": total_campaigns,
        "total_emails_sent": total_emails_sent,
        "sent_count": sent_count,
        "delivered_count": delivered_count,
        "opened_count": opened_count,
        "not_opened_count": not_opened_count,
        "replied_count": replied_count,
        "failed_count": failed_count,
        "open_rate": open_rate,
        "reply_rate": reply_rate
    }
    
    return render_template("dashboard/index.html", stats=stats, recent_campaigns=recent_campaigns)

@dashboard_bp.route("/api/dashboard/stats")
@login_required
def stats_api():
    user_id = session.get("user_id")
    db = get_db()
    
    delivered_count = db.sent_emails.count_documents({"user_id": user_id, "status": {"$in": ["delivered", "opened", "replied"]}})
    opened_count = db.sent_emails.count_documents({"user_id": user_id, "status": {"$in": ["opened", "replied"]}})
    replied_count = db.sent_emails.count_documents({"user_id": user_id, "status": "replied"})
    failed_count = db.sent_emails.count_documents({"user_id": user_id, "status": "failed"})
    not_opened_count = max(0, delivered_count - opened_count)
    
    chart_data = {
        "labels": ["Delivered (Unopened)", "Opened", "Replied", "Failed"],
        "series": [not_opened_count, max(0, opened_count - replied_count), replied_count, failed_count]
    }
    return jsonify(chart_data)
