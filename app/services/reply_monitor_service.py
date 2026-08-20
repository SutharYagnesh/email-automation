import imaplib
import email
import threading
import time
from datetime import datetime
from bson import ObjectId
from app.db import get_db
from app.services.sender_service import get_sender_decrypted

_monitor_thread = None
_stop_monitor_event = threading.Event()

def check_sender_replies(sender_id: str, user_id: str = None) -> int:
    """Connect to Gmail via IMAP and scan inbox for replies matching sent emails."""
    sender = get_sender_decrypted(sender_id, user_id)
    if not sender or not sender.get("app_password"):
        return 0
        
    username = sender["username"]
    password = sender["app_password"]
    
    replies_found = 0
    db = get_db()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(username, password)
        mail.select("inbox")
        
        # Search for UNSEEN or recent emails
        status, data = mail.search(None, '(UNSEEN)')
        if status != "OK" or not data[0]:
            # fallback to search ALL recent
            status, data = mail.search(None, 'ALL')
            
        if status == "OK" and data[0]:
            mail_ids = data[0].split()
            # Inspect last 50 emails
            for m_id in mail_ids[-50:]:
                res, msg_data = mail.fetch(m_id, "(RFC822.HEADER)")
                if res != "OK":
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        in_reply_to = msg.get("In-Reply-To", "").strip()
                        references = msg.get("References", "").strip()
                        from_header = msg.get("From", "").strip()
                        subject_header = msg.get("Subject", "").strip()
                        
                        # Extract sender email address from From header
                        from_email = ""
                        if "<" in from_header and ">" in from_header:
                            from_email = from_header.split("<")[1].split(">")[0].strip().lower()
                        else:
                            from_email = from_header.strip().lower()
                            
                        # Try matching by Message-ID
                        matched_sent = None
                        if in_reply_to:
                            matched_sent = db.sent_emails.find_one({"message_id": in_reply_to, "sender_id": sender_id})
                            
                        if not matched_sent and references:
                            for ref in references.split():
                                matched_sent = db.sent_emails.find_one({"message_id": ref.strip(), "sender_id": sender_id})
                                if matched_sent:
                                    break
                                    
                        # Fallback match by recipient email and subject match (e.g. Re: ...)
                        if not matched_sent and from_email:
                            clean_subj = subject_header.lower().replace("re:", "").strip()
                            matched_sent = db.sent_emails.find_one({
                                "recipient_email": from_email,
                                "sender_id": sender_id,
                                "status": {"$in": ["sent", "delivered", "opened"]}
                            })
                            
                        if matched_sent and matched_sent.get("status") != "replied":
                            now = datetime.utcnow()
                            db.sent_emails.update_one(
                                {"_id": matched_sent["_id"]},
                                {"$set": {"status": "replied", "replied_at": now}}
                            )
                            # Increment campaign replied_count
                            if matched_sent.get("campaign_id"):
                                try:
                                    db.campaigns.update_one(
                                        {"_id": ObjectId(matched_sent["campaign_id"])},
                                        {"$inc": {"replied_count": 1}}
                                    )
                                except Exception:
                                    pass
                            replies_found += 1
                            
        mail.logout()
    except Exception as e:
        print(f"[IMAP Reply Monitor Error for {username}]: {e}")
        
    return replies_found

def start_background_reply_monitor(interval_seconds: int = 120):
    """Start global background polling thread to check replies for all connected senders."""
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
        
    _stop_monitor_event.clear()
    
    def _loop():
        while not _stop_monitor_event.is_set():
            try:
                db = get_db()
                active_senders = list(db.sender_accounts.find({"status": {"$in": ["connected", "warning"]}}))
                for sender in active_senders:
                    check_sender_replies(str(sender["_id"]), str(sender["user_id"]))
            except Exception as ex:
                print(f"[Reply Monitor Loop Error]: {ex}")
            time.sleep(interval_seconds)
            
    _monitor_thread = threading.Thread(target=_loop, daemon=True)
    _monitor_thread.start()
    print("[Reply Monitor Service] Background IMAP poller started.")

def stop_background_reply_monitor():
    """Stop reply monitor thread."""
    _stop_monitor_event.set()
