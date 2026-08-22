import re
import os
from datetime import datetime
from bson import ObjectId
from werkzeug.utils import secure_filename
from app.db import get_db
from config import Config

def create_template(user_id: str, name: str, subject: str, body_html: str, body_text: str = "", attachments: list = None) -> tuple[bool, str, dict]:
    """Create a new email template."""
    db = get_db()
    name = name.strip()
    subject = subject.strip()
    if not name or not subject or not body_html:
        return False, "Template name, subject, and HTML body are required.", {}
        
    doc = {
        "user_id": user_id,
        "name": name,
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text or "",
        "attachments": attachments or [],  # list of dicts: {"filename": ..., "path": ..., "size": ...}
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.templates.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return True, "Template created successfully.", doc

def update_template(template_id: str, user_id: str, data: dict) -> tuple[bool, str]:
    """Update existing email template."""
    db = get_db()
    try:
        tid = ObjectId(template_id)
    except Exception:
        return False, "Invalid template ID."
        
    update_doc = {
        "name": data.get("name", "").strip(),
        "subject": data.get("subject", "").strip(),
        "body_html": data.get("body_html", ""),
        "body_text": data.get("body_text", ""),
        "attachments": data.get("attachments", []),
        "updated_at": datetime.utcnow()
    }
    
    result = db.templates.update_one({"_id": tid, "user_id": user_id}, {"$set": update_doc})
    if result.matched_count == 0:
        return False, "Template not found."
    return True, "Template updated successfully."

def delete_template(template_id: str, user_id: str) -> tuple[bool, str]:
    """Delete a template."""
    db = get_db()
    try:
        tid = ObjectId(template_id)
    except Exception:
        return False, "Invalid template ID."
    result = db.templates.delete_one({"_id": tid, "user_id": user_id})
    if result.deleted_count == 0:
        return False, "Template not found."
    return True, "Template deleted."

def get_templates(user_id: str) -> list:
    """Fetch all templates for user."""
    db = get_db()
    templates = list(db.templates.find({"user_id": user_id}).sort("created_at", -1))
    for t in templates:
        t["_id"] = str(t["_id"])
    return templates

def get_template_by_id(template_id: str, user_id: str = None) -> dict:
    """Get single template document."""
    db = get_db()
    try:
        tid = ObjectId(template_id)
    except Exception:
        return None
    query = {"_id": tid}
    if user_id:
        query["user_id"] = user_id
    t = db.templates.find_one(query)
    if t:
        t["_id"] = str(t["_id"])
    return t

def render_template_variables(text_content: str, contact_data: dict) -> str:
    """
    Replace placeholders in template text/HTML with contact data.
    Supported tags: {{name}}, {{email}}, {{company_name}}, and {{custom.field_name}} or {{field_name}}
    """
    if not text_content:
        return ""
        
    name = contact_data.get("name", "")
    email = contact_data.get("email", "")
    company_name = contact_data.get("company_name", "")
    custom = contact_data.get("custom_fields", {})
    
    rendered = text_content
    rendered = re.sub(r"\{\{\s*name\s*\}\}", name or "Valued Customer", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\{\{\s*email\s*\}\}", email or "", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\{\{\s*company_name\s*\}\}", company_name or "your company", rendered, flags=re.IGNORECASE)
    
    # Custom fields replacement
    for k, v in custom.items():
        key_escaped = re.escape(k)
        pattern_dotted = r"\{\{\s*custom\." + key_escaped + r"\s*\}\}"
        pattern_direct = r"\{\{\s*" + key_escaped + r"\s*\}\}"
        rendered = re.sub(pattern_dotted, str(v), rendered, flags=re.IGNORECASE)
        rendered = re.sub(pattern_direct, str(v), rendered, flags=re.IGNORECASE)
        
    # Clean up any leftover unmatched double curly brackets to clean text
    rendered = re.sub(r"\{\{\s*custom\.[^}]+\s*\}\}", "", rendered)
    
    return rendered

def save_uploaded_attachment(file_storage) -> dict:
    """Save an uploaded template attachment file securely."""
    try:
        if not file_storage or not hasattr(file_storage, 'filename') or not file_storage.filename:
            return None
            
        filename = secure_filename(file_storage.filename)
        if not filename:
            return None
            
        folder = os.path.join(Config.UPLOAD_FOLDER, "template_attachments")
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            folder = "/tmp"
            
        unique_name = f"{int(datetime.utcnow().timestamp())}_{filename}"
        file_path = os.path.join(folder, unique_name)
        file_storage.save(file_path)
        
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        return {
            "original_name": filename,
            "saved_name": unique_name,
            "path": file_path,
            "size": size
        }
    except Exception as e:
        print(f"[Save Attachment Warning] {e}")
        return None
