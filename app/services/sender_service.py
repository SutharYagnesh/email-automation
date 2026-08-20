import smtplib
import imaplib
import dns.resolver
from datetime import datetime
from bson import ObjectId
from app.db import get_db
from app.security import encrypt_credential, decrypt_credential, mask_password

def create_sender_account(user_id: str, username: str, app_password: str, sender_name: str = "", reply_to: str = "", smtp_port: int = 465) -> tuple[bool, str, dict]:
    """Add a new Gmail sender account with encrypted App Password."""
    db = get_db()
    username = username.strip().lower()
    if not username or "@" not in username:
        return False, "Valid Gmail username (email) is required.", {}
    if not app_password:
        return False, "Gmail App Password is required.", {}
        
    existing = db.sender_accounts.find_one({"user_id": user_id, "username": username})
    if existing:
        return False, f"Sender account '{username}' already exists.", {}
        
    encrypted_pwd = encrypt_credential(app_password)
    port = int(smtp_port) if smtp_port else 465
    
    doc = {
        "user_id": user_id,
        "username": username,
        "encrypted_app_password": encrypted_pwd,
        "sender_name": sender_name.strip() or username.split("@")[0].title(),
        "reply_to": reply_to.strip().lower() or username,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": port,
        "use_ssl": (port == 465),
        "status": "untested",
        "status_message": "Connection not tested yet.",
        "last_tested_at": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.sender_accounts.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc["app_password_masked"] = mask_password(app_password)
    doc.pop("encrypted_app_password", None)
    return True, "Sender account added successfully.", doc

def update_sender_account(sender_id: str, user_id: str, data: dict) -> tuple[bool, str]:
    """Update sender account configuration."""
    db = get_db()
    try:
        sid = ObjectId(sender_id)
    except Exception:
        return False, "Invalid sender account ID."
        
    update_fields = {
        "sender_name": data.get("sender_name", "").strip(),
        "reply_to": data.get("reply_to", "").strip().lower(),
        "updated_at": datetime.utcnow()
    }
    
    if "smtp_port" in data:
        port = int(data["smtp_port"])
        update_fields["smtp_port"] = port
        update_fields["use_ssl"] = (port == 465)
        
    if data.get("app_password"):
        update_fields["encrypted_app_password"] = encrypt_credential(data["app_password"])
        update_fields["status"] = "untested"
        update_fields["status_message"] = "App password changed. Test connection required."
        
    result = db.sender_accounts.update_one({"_id": sid, "user_id": user_id}, {"$set": update_fields})
    if result.matched_count == 0:
        return False, "Sender account not found."
    return True, "Sender account updated successfully."

def delete_sender_account(sender_id: str, user_id: str) -> tuple[bool, str]:
    """Delete sender account."""
    db = get_db()
    try:
        sid = ObjectId(sender_id)
    except Exception:
        return False, "Invalid sender account ID."
    result = db.sender_accounts.delete_one({"_id": sid, "user_id": user_id})
    if result.deleted_count == 0:
        return False, "Sender account not found."
    return True, "Sender account deleted."

def get_sender_accounts(user_id: str) -> list:
    """Fetch all sender accounts for user with passwords masked."""
    db = get_db()
    senders = list(db.sender_accounts.find({"user_id": user_id}).sort("created_at", -1))
    for s in senders:
        s["_id"] = str(s["_id"])
        s["app_password_masked"] = "••••••••••••"
        s.pop("encrypted_app_password", None)
    return senders

def get_sender_decrypted(sender_id: str, user_id: str = None) -> dict:
    """Internal helper to retrieve sender with decrypted password for SMTP/IMAP operations."""
    db = get_db()
    try:
        sid = ObjectId(sender_id)
    except Exception:
        return None
    query = {"_id": sid}
    if user_id:
        query["user_id"] = user_id
    sender = db.sender_accounts.find_one(query)
    if not sender:
        return None
    sender["_id"] = str(sender["_id"])
    sender["app_password"] = decrypt_credential(sender.get("encrypted_app_password", ""))
    return sender

def test_sender_connection(sender_id: str, user_id: str) -> tuple[bool, str]:
    """Test SMTP and IMAP connection using stored Gmail App Password."""
    sender = get_sender_decrypted(sender_id, user_id)
    if not sender:
        return False, "Sender account not found."
        
    username = sender["username"]
    password = sender["app_password"]
    smtp_host = sender.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(sender.get("smtp_port", 465))
    
    if not password:
        return False, "No valid password stored for this account."
        
    # 1. Test SMTP Connection
    smtp_success = False
    smtp_error = ""
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, 465, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        server.login(username, password)
        server.quit()
        smtp_success = True
    except Exception as e:
        smtp_error = str(e)
        
    if not smtp_success:
        msg = f"SMTP Connection failed: {smtp_error}"
        get_db().sender_accounts.update_one(
            {"_id": ObjectId(sender_id)},
            {"$set": {"status": "error", "status_message": msg, "last_tested_at": datetime.utcnow()}}
        )
        return False, msg
        
    # 2. Test IMAP Connection (for reply tracking)
    imap_success = False
    imap_error = ""
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(username, password)
        imap.logout()
        imap_success = True
    except Exception as e:
        imap_error = str(e)
        
    if not imap_success:
        msg = f"SMTP connected, but IMAP (Reply tracking) failed: {imap_error}"
        get_db().sender_accounts.update_one(
            {"_id": ObjectId(sender_id)},
            {"$set": {"status": "warning", "status_message": msg, "last_tested_at": datetime.utcnow()}}
        )
        return True, "SMTP connection successful! Note: IMAP warning (Reply tracking might be limited)."
        
    # Success both
    get_db().sender_accounts.update_one(
        {"_id": ObjectId(sender_id)},
        {"$set": {"status": "connected", "status_message": "SMTP & IMAP connections successful.", "last_tested_at": datetime.utcnow()}}
    )
    return True, "SMTP & IMAP connections verified successfully!"

def check_domain_deliverability(domain: str) -> dict:
    """Run deliverability checklist verification for SPF, DKIM, DMARC, and MX records."""
    domain = domain.strip().lower()
    if "@" in domain:
        domain = domain.split("@")[-1]
        
    results = {
        "domain": domain,
        "spf": {"status": "unknown", "record": "", "details": ""},
        "dkim": {"status": "unknown", "record": "", "details": "Google DKIM record selector depends on your Google Workspace settings."},
        "dmarc": {"status": "unknown", "record": "", "details": ""},
        "mx": {"status": "unknown", "record": "", "details": ""},
        "deliverability_score": 0
    }
    
    score = 0
    
    # 1. Check MX Records
    try:
        mx_answers = dns.resolver.resolve(domain, 'MX')
        mx_records = [str(r.exchange).rstrip('.') for r in mx_answers]
        results["mx"] = {
            "status": "pass",
            "record": ", ".join(mx_records),
            "details": "MX records found."
        }
        score += 25
    except Exception as e:
        results["mx"] = {"status": "fail", "record": "None", "details": f"No MX records found: {str(e)}"}
        
    # 2. Check SPF Record
    try:
        txt_answers = dns.resolver.resolve(domain, 'TXT')
        spf_found = False
        for txt in txt_answers:
            txt_str = str(txt).strip('"')
            if txt_str.startswith("v=spf1"):
                spf_found = True
                results["spf"]["record"] = txt_str
                if "include:_spf.google.com" in txt_str or "include:spf.google.com" in txt_str or domain == "gmail.com":
                    results["spf"]["status"] = "pass"
                    results["spf"]["details"] = "Valid SPF record configured with Google SPF inclusion."
                    score += 35
                else:
                    results["spf"]["status"] = "warning"
                    results["spf"]["details"] = "SPF record exists, but does not include Google SPF ('include:_spf.google.com')."
                    score += 20
                break
        if not spf_found:
            results["spf"] = {"status": "fail", "record": "Missing", "details": "No SPF TXT record starting with 'v=spf1' found."}
    except Exception as e:
        results["spf"] = {"status": "fail", "record": "Missing", "details": f"SPF lookup failed: {str(e)}"}
        
    # 3. Check DMARC Record
    try:
        dmarc_domain = f"_dmarc.{domain}"
        dmarc_answers = dns.resolver.resolve(dmarc_domain, 'TXT')
        dmarc_found = False
        for txt in dmarc_answers:
            txt_str = str(txt).strip('"')
            if txt_str.startswith("v=DMARC1"):
                dmarc_found = True
                results["dmarc"]["record"] = txt_str
                results["dmarc"]["status"] = "pass"
                results["dmarc"]["details"] = "DMARC policy record configured."
                score += 25
                break
        if not dmarc_found:
            results["dmarc"] = {"status": "warning", "record": "Missing", "details": "No DMARC record found at _dmarc." + domain}
            score += 5
    except Exception:
        results["dmarc"] = {"status": "warning", "record": "Missing", "details": f"No DMARC record found at _dmarc.{domain}"}
        score += 5
        
    # 4. DKIM Note for Gmail/Google Workspace
    if domain == "gmail.com":
        results["dkim"] = {"status": "pass", "record": "Google Default DKIM", "details": "Google handles DKIM automatically for @gmail.com addresses."}
        score += 15
    else:
        results["dkim"] = {"status": "info", "record": "Selector dependant", "details": "For custom domains on Google Workspace, enable DKIM in Admin Console -> Apps -> Google Workspace -> Gmail -> Authenticate email."}
        score += 15
        
    results["deliverability_score"] = score
    return results
