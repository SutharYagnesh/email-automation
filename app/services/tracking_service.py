import base64
from datetime import datetime
from bson import ObjectId
from flask import request, Response
from app.db import get_db

# 1x1 Transparent PNG binary data
TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

def record_email_open(tracking_id: str) -> Response:
    """Record open event from tracking pixel and return transparent 1x1 PNG."""
    db = get_db()
    if tracking_id and tracking_id != "generic":
        sent_email = db.sent_emails.find_one({"tracking_id": tracking_id})
        if sent_email:
            # Update status if not already opened/replied
            if sent_email.get("status") in ["sent", "delivered"]:
                now = datetime.utcnow()
                db.sent_emails.update_one(
                    {"_id": sent_email["_id"]},
                    {"$set": {"status": "opened", "opened_at": now}}
                )
                # Update campaign aggregate counter
                if sent_email.get("campaign_id"):
                    try:
                        db.campaigns.update_one(
                            {"_id": ObjectId(sent_email["campaign_id"])},
                            {"$inc": {"opened_count": 1}}
                        )
                    except Exception:
                        pass
                        
            # Record detailed tracking event log
            event_doc = {
                "sent_email_id": str(sent_email["_id"]),
                "campaign_id": sent_email.get("campaign_id"),
                "tracking_id": tracking_id,
                "event_type": "open",
                "ip_address": request.headers.get("X-Forwarded-For", request.remote_addr),
                "user_agent": request.headers.get("User-Agent", ""),
                "timestamp": datetime.utcnow()
            }
            db.tracking_events.insert_one(event_doc)

    res = Response(TRANSPARENT_PNG, mimetype="image/png")
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    return res

def process_unsubscribe(tracking_id: str) -> tuple[bool, str, str]:
    """Process contact unsubscribe request."""
    db = get_db()
    if not tracking_id:
        return False, "Invalid unsubscribe token.", ""
        
    sent_email = db.sent_emails.find_one({"tracking_id": tracking_id})
    recipient_email = None
    
    if sent_email:
        recipient_email = sent_email.get("recipient_email")
        user_id = sent_email.get("user_id")
        contact_id = sent_email.get("contact_id")
        
        # Mark contact as unsubscribed
        if contact_id:
            try:
                db.contacts.update_one(
                    {"_id": ObjectId(contact_id)},
                    {"$set": {"unsubscribed": True, "unsubscribed_at": datetime.utcnow()}}
                )
            except Exception:
                pass
        elif user_id and recipient_email:
            db.contacts.update_many(
                {"user_id": user_id, "email": recipient_email},
                {"$set": {"unsubscribed": True, "unsubscribed_at": datetime.utcnow()}}
            )
        return True, "You have been successfully unsubscribed.", recipient_email
        
    return False, "Unsubscribe request processed.", ""
