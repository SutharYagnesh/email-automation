import uuid
import time
import threading
from datetime import datetime
from bson import ObjectId
from app.db import get_db
from app.services.sender_service import get_sender_decrypted
from app.services.template_service import get_template_by_id, render_template_variables
from app.services.smtp_service import send_single_email

_active_campaign_threads = {}

def create_campaign(
    user_id: str,
    name: str,
    sender_id: str,
    template_id: str,
    recipient_type: str,  # 'groups' or 'contacts'
    group_ids: list = None,
    contact_ids: list = None,
    delay_seconds: float = 2.0
) -> tuple[bool, str, dict]:
    """Create a new email campaign draft."""
    db = get_db()
    name = name.strip()
    if not name or not sender_id or not template_id:
        return False, "Campaign name, sender account, and template are required.", {}
        
    # Calculate recipient contacts list & filter duplicates / unsubscribed
    recipients = resolve_campaign_recipients(user_id, recipient_type, group_ids, contact_ids)
    
    doc = {
        "user_id": user_id,
        "name": name,
        "sender_id": sender_id,
        "template_id": template_id,
        "recipient_type": recipient_type,
        "group_ids": group_ids or [],
        "contact_ids": contact_ids or [],
        "delay_seconds": max(0.5, float(delay_seconds)),
        "status": "draft",
        "total_recipients": len(recipients),
        "sent_count": 0,
        "delivered_count": 0,
        "opened_count": 0,
        "replied_count": 0,
        "failed_count": 0,
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None
    }
    
    result = db.campaigns.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return True, f"Campaign created with {len(recipients)} valid recipients.", doc

def resolve_campaign_recipients(user_id: str, recipient_type: str, group_ids: list = None, contact_ids: list = None) -> list:
    """Resolve distinct, non-unsubscribed contacts for a campaign."""
    db = get_db()
    query = {"user_id": user_id, "unsubscribed": False}
    
    if recipient_type == "groups" and group_ids:
        query["group_ids"] = {"$in": group_ids}
    elif recipient_type == "contacts" and contact_ids:
        c_oids = []
        for cid in contact_ids:
            try:
                c_oids.append(ObjectId(cid))
            except Exception:
                pass
        query["_id"] = {"$in": c_oids}
        
    raw_contacts = list(db.contacts.find(query))
    
    # Filter duplicate emails
    seen_emails = set()
    unique_contacts = []
    for c in raw_contacts:
        email = c.get("email", "").strip().lower()
        if email and email not in seen_emails:
            seen_emails.add(email)
            c["_id"] = str(c["_id"])
            unique_contacts.append(c)
            
    return unique_contacts

def launch_campaign(campaign_id: str, user_id: str) -> tuple[bool, str]:
    """Trigger campaign sending in an asynchronous background thread."""
    db = get_db()
    try:
        cid = ObjectId(campaign_id)
    except Exception:
        return False, "Invalid campaign ID."
        
    campaign = db.campaigns.find_one({"_id": cid, "user_id": user_id})
    if not campaign:
        return False, "Campaign not found."
        
    if campaign["status"] in ["sending", "completed"]:
        return False, f"Campaign is currently {campaign['status']}."
        
    # Mark status as queued/sending
    db.campaigns.update_one(
        {"_id": cid},
        {"$set": {"status": "sending", "started_at": datetime.utcnow()}}
    )
    
    # Launch background thread
    t = threading.Thread(target=_run_campaign_dispatch, args=(campaign_id, user_id), daemon=True)
    _active_campaign_threads[campaign_id] = t
    t.start()
    
    return True, "Campaign sending launched in background."

def _run_campaign_dispatch(campaign_id: str, user_id: str):
    """Background worker function that processes throttled email sending."""
    db = get_db()
    try:
        cid = ObjectId(campaign_id)
        campaign = db.campaigns.find_one({"_id": cid})
        if not campaign:
            return
            
        sender = get_sender_decrypted(campaign["sender_id"], user_id)
        template = get_template_by_id(campaign["template_id"], user_id)
        
        if not sender or not template or not sender.get("app_password"):
            db.campaigns.update_one(
                {"_id": cid},
                {"$set": {"status": "failed", "error_message": "Sender account or template configuration missing."}}
            )
            return
            
        recipients = resolve_campaign_recipients(
            user_id,
            campaign.get("recipient_type", "contacts"),
            campaign.get("group_ids", []),
            campaign.get("contact_ids", [])
        )
        
        # Get list of emails already sent in this campaign (duplicate sending prevention)
        already_sent_emails = set(
            db.sent_emails.distinct("recipient_email", {"campaign_id": campaign_id})
        )
        
        delay = float(campaign.get("delay_seconds", 2.0))
        
        for contact in recipients:
            recipient_email = contact["email"]
            
            # Check if campaign was cancelled or paused
            curr_camp = db.campaigns.find_one({"_id": cid}, {"status": 1})
            if curr_camp and curr_camp.get("status") in ["paused", "cancelled"]:
                break
                
            # Skip if already sent in this campaign
            if recipient_email in already_sent_emails:
                continue
                
            tracking_id = str(uuid.uuid4())
            
            # Personalize subject & body
            rendered_subject = render_template_variables(template["subject"], contact)
            rendered_html = render_template_variables(template["body_html"], contact)
            rendered_text = render_template_variables(template.get("body_text", ""), contact)
            
            # Send email via SMTP
            success, error_msg, message_id = send_single_email(
                smtp_username=sender["username"],
                smtp_password=sender["app_password"],
                sender_name=sender.get("sender_name", ""),
                reply_to=sender.get("reply_to", ""),
                recipient_email=recipient_email,
                subject=rendered_subject,
                body_html=rendered_html,
                body_text=rendered_text,
                attachments=template.get("attachments", []),
                tracking_id=tracking_id,
                host=sender.get("smtp_host", "smtp.gmail.com"),
                port=sender.get("smtp_port", 465)
            )
            
            sent_status = "delivered" if success else "failed"
            
            # Record sent email document
            sent_doc = {
                "campaign_id": campaign_id,
                "user_id": user_id,
                "contact_id": contact["_id"],
                "sender_id": campaign["sender_id"],
                "recipient_email": recipient_email,
                "recipient_name": contact.get("name", ""),
                "subject": rendered_subject,
                "message_id": message_id,
                "tracking_id": tracking_id,
                "status": sent_status,
                "error_message": error_msg if not success else "",
                "sent_at": datetime.utcnow(),
                "opened_at": None,
                "replied_at": None
            }
            db.sent_emails.insert_one(sent_doc)
            
            # Update campaign stats
            inc_field = {"sent_count": 1, "delivered_count": 1} if success else {"sent_count": 1, "failed_count": 1}
            db.campaigns.update_one({"_id": cid}, {"$inc": inc_field})
            
            already_sent_emails.add(recipient_email)
            
            # Throttling delay
            time.sleep(delay)
            
        # Finish campaign
        db.campaigns.update_one(
            {"_id": cid},
            {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
        )
    except Exception as e:
        print(f"[Campaign Dispatch Error] {e}")
        db.campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {"status": "failed", "error_message": str(e)}}
        )

def get_campaigns(user_id: str) -> list:
    """List all campaigns for user."""
    db = get_db()
    campaigns = list(db.campaigns.find({"user_id": user_id}).sort("created_at", -1))
    for c in campaigns:
        c["_id"] = str(c["_id"])
    return campaigns

def get_campaign_detail(campaign_id: str, user_id: str) -> dict:
    """Get full campaign object with recipient log list."""
    db = get_db()
    try:
        cid = ObjectId(campaign_id)
    except Exception:
        return None
    campaign = db.campaigns.find_one({"_id": cid, "user_id": user_id})
    if not campaign:
        return None
    campaign["_id"] = str(campaign["_id"])
    
    # Get sent email logs
    sent_logs = list(db.sent_emails.find({"campaign_id": campaign_id}).sort("sent_at", -1))
    for log in sent_logs:
        log["_id"] = str(log["_id"])
    campaign["sent_emails"] = sent_logs
    return campaign

def delete_campaign(campaign_id: str, user_id: str) -> tuple[bool, str]:
    """Delete a campaign and its sent email logs."""
    db = get_db()
    try:
        cid = ObjectId(campaign_id)
    except Exception:
        return False, "Invalid campaign ID."
    result = db.campaigns.delete_one({"_id": cid, "user_id": user_id})
    if result.deleted_count > 0:
        db.sent_emails.delete_many({"campaign_id": campaign_id, "user_id": user_id})
        return True, "Campaign deleted successfully."
    return False, "Campaign not found."

def add_sends_to_campaign(
    campaign_id: str,
    user_id: str,
    template_id: str = None,
    recipient_type: str = "groups",
    group_ids: list = None,
    contact_ids: list = None,
    delay_seconds: float = None
) -> tuple[bool, str]:
    """Add additional recipients and/or change template for an existing campaign."""
    db = get_db()
    try:
        cid = ObjectId(campaign_id)
    except Exception:
        return False, "Invalid campaign ID."
        
    campaign = db.campaigns.find_one({"_id": cid, "user_id": user_id})
    if not campaign:
        return False, "Campaign not found."
        
    if campaign.get("status") == "sending":
        return False, "Campaign is currently sending. Please wait until dispatch completes."
        
    # Determine new target recipients
    recipients = resolve_campaign_recipients(user_id, recipient_type, group_ids, contact_ids)
    
    # Calculate how many of these recipients have NOT been sent to yet
    already_sent_emails = set(
        db.sent_emails.distinct("recipient_email", {"campaign_id": campaign_id})
    )
    new_unSent_contacts = [r for r in recipients if r["email"] not in already_sent_emails]
    
    if not new_unSent_contacts:
        return False, "All selected recipients have already received an email from this campaign."
        
    update_doc = {
        "status": "sending",
        "started_at": datetime.utcnow()
    }
    
    if template_id:
        update_doc["template_id"] = template_id
    if delay_seconds:
        update_doc["delay_seconds"] = max(0.5, float(delay_seconds))
        
    # Add new recipient group/contact IDs to campaign record
    if recipient_type == "groups" and group_ids:
        db.campaigns.update_one({"_id": cid}, {"$addToSet": {"group_ids": {"$each": group_ids}}})
    elif recipient_type == "contacts" and contact_ids:
        db.campaigns.update_one({"_id": cid}, {"$addToSet": {"contact_ids": {"$each": contact_ids}}})
        
    db.campaigns.update_one(
        {"_id": cid},
        {
            "$set": update_doc,
            "$inc": {"total_recipients": len(new_unSent_contacts)}
        }
    )
    
    # Launch background thread
    t = threading.Thread(target=_run_campaign_dispatch, args=(campaign_id, user_id), daemon=True)
    _active_campaign_threads[campaign_id] = t
    t.start()
    
    return True, f"Dispatched {len(new_unSent_contacts)} additional email(s) for this campaign."

