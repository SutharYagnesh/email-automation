import os
import pandas as pd
from datetime import datetime
from bson import ObjectId
from app.db import get_db

def create_contact(user_id: str, email: str, name: str = "", company_name: str = "", custom_fields: dict = None, group_ids: list = None, label_ids: list = None) -> tuple[bool, str, dict]:
    """Create a single contact, checking for email duplicates."""
    db = get_db()
    email = email.strip().lower()
    if not email:
        return False, "Email address is required.", {}
        
    existing = db.contacts.find_one({"user_id": user_id, "email": email})
    if existing:
        return False, f"Contact with email '{email}' already exists.", {}
        
    doc = {
        "user_id": user_id,
        "email": email,
        "name": name.strip(),
        "company_name": company_name.strip(),
        "custom_fields": custom_fields or {},
        "group_ids": group_ids or [],
        "label_ids": label_ids or [],
        "unsubscribed": False,
        "unsubscribed_at": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.contacts.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return True, "Contact created successfully.", doc

def update_contact(contact_id: str, user_id: str, data: dict) -> tuple[bool, str]:
    """Update contact details."""
    db = get_db()
    try:
        cid = ObjectId(contact_id)
    except Exception:
        return False, "Invalid contact ID."
        
    update_doc = {
        "name": data.get("name", "").strip(),
        "company_name": data.get("company_name", "").strip(),
        "custom_fields": data.get("custom_fields", {}),
        "group_ids": data.get("group_ids", []),
        "label_ids": data.get("label_ids", []),
        "updated_at": datetime.utcnow()
    }
    
    # If email changed, check for duplicate
    if "email" in data:
        new_email = data["email"].strip().lower()
        existing = db.contacts.find_one({"user_id": user_id, "email": new_email, "_id": {"$ne": cid}})
        if existing:
            return False, f"Email '{new_email}' is already used by another contact."
        update_doc["email"] = new_email
        
    result = db.contacts.update_one({"_id": cid, "user_id": user_id}, {"$set": update_doc})
    if result.matched_count == 0:
        return False, "Contact not found."
    return True, "Contact updated successfully."

def bulk_add_contacts_to_group(contact_ids: list, group_id: str, user_id: str) -> tuple[bool, str]:
    """Assign multiple contacts to a group."""
    if not contact_ids or not group_id:
        return False, "No contacts or group selected."
    db = get_db()
    c_oids = []
    for cid in contact_ids:
        try:
            c_oids.append(ObjectId(cid))
        except Exception:
            pass
            
    if not c_oids:
        return False, "Invalid contact IDs provided."
        
    result = db.contacts.update_many(
        {"_id": {"$in": c_oids}, "user_id": user_id},
        {"$addToSet": {"group_ids": group_id}, "$set": {"updated_at": datetime.utcnow()}}
    )
    return True, f"Successfully assigned {result.modified_count} contact(s) to group."


def delete_contact(contact_id: str, user_id: str) -> tuple[bool, str]:
    """Delete a contact by ID."""
    db = get_db()
    try:
        cid = ObjectId(contact_id)
    except Exception:
        return False, "Invalid contact ID."
    result = db.contacts.delete_one({"_id": cid, "user_id": user_id})
    if result.deleted_count == 0:
        return False, "Contact not found."
    return True, "Contact deleted successfully."

def get_contacts(user_id: str, group_id: str = None, label_id: str = None, search: str = None) -> list:
    """Fetch contacts with optional group, label, or text filtering."""
    db = get_db()
    query = {"user_id": user_id}
    
    if group_id:
        query["group_ids"] = group_id
    if label_id:
        query["label_ids"] = label_id
    if search:
        s = search.strip()
        query["$or"] = [
            {"email": {"$regex": s, "$options": "i"}},
            {"name": {"$regex": s, "$options": "i"}},
            {"company_name": {"$regex": s, "$options": "i"}}
        ]
        
    contacts = list(db.contacts.find(query).sort("created_at", -1))
    for c in contacts:
        c["_id"] = str(c["_id"])
    return contacts

def import_contacts_from_file(file_path: str, user_id: str, group_ids: list = None, label_ids: list = None) -> tuple[bool, str, dict]:
    """Import contacts from CSV or XLSX with automatic column mapping and duplicate skipping."""
    if not os.path.exists(file_path):
        return False, "Uploaded file not found.", {"imported": 0, "skipped": 0, "errors": ["File missing."]}
        
    ext = file_path.rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv":
            df = pd.read_csv(file_path)
        elif ext in ["xlsx", "xls"]:
            df = pd.read_excel(file_path)
        else:
            return False, "Unsupported file format. Please upload CSV or XLSX.", {"imported": 0, "skipped": 0, "errors": []}
    except Exception as e:
        return False, f"Failed to parse file: {str(e)}", {"imported": 0, "skipped": 0, "errors": [str(e)]}
        
    if df.empty:
        return False, "Uploaded file is empty.", {"imported": 0, "skipped": 0, "errors": []}
        
    # Standardize column headers (lowercase, stripped)
    column_map = {}
    for col in df.columns:
        norm = str(col).strip().lower()
        if norm in ["email", "e-mail", "email_address", "email address"]:
            column_map[col] = "email"
        elif norm in ["name", "full_name", "full name", "contact_name", "first_name"]:
            column_map[col] = "name"
        elif norm in ["company", "company_name", "company name", "organization"]:
            column_map[col] = "company_name"
            
    df = df.rename(columns=column_map)
    
    if "email" not in df.columns:
        return False, "File must contain an 'Email' column.", {"imported": 0, "skipped": 0, "errors": []}
        
    db = get_db()
    imported_count = 0
    skipped_count = 0
    errors = []
    
    for idx, row in df.iterrows():
        raw_email = str(row.get("email", "")).strip().lower()
        if not raw_email or raw_email == "nan" or "@" not in raw_email:
            skipped_count += 1
            continue
            
        name = str(row.get("name", "")).strip() if "name" in df.columns and str(row.get("name", "")) != "nan" else ""
        company = str(row.get("company_name", "")).strip() if "company_name" in df.columns and str(row.get("company_name", "")) != "nan" else ""
        
        # Extract custom extra fields
        custom_fields = {}
        for col in df.columns:
            if col not in ["email", "name", "company_name"]:
                val = row.get(col)
                if pd.notna(val):
                    custom_fields[str(col).strip()] = str(val).strip()
                    
        # Check duplicate
        existing = db.contacts.find_one({"user_id": user_id, "email": raw_email})
        if existing:
            # Update groups/labels if not assigned
            db.contacts.update_one(
                {"_id": existing["_id"]},
                {
                    "$addToSet": {
                        "group_ids": {"$each": group_ids or []},
                        "label_ids": {"$each": label_ids or []}
                    },
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            skipped_count += 1
            continue
            
        contact_doc = {
            "user_id": user_id,
            "email": raw_email,
            "name": name,
            "company_name": company,
            "custom_fields": custom_fields,
            "group_ids": group_ids or [],
            "label_ids": label_ids or [],
            "unsubscribed": False,
            "unsubscribed_at": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            db.contacts.insert_one(contact_doc)
            imported_count += 1
        except Exception as ex:
            skipped_count += 1
            errors.append(f"Row {idx + 2}: {str(ex)}")
            
    summary = {"imported": imported_count, "skipped": skipped_count, "errors": errors}
    return True, f"Import finished: {imported_count} contacts added, {skipped_count} duplicates/invalid skipped.", summary

# Groups Management
def create_group(user_id: str, name: str, description: str = "") -> tuple[bool, str, dict]:
    """Create a contact group."""
    db = get_db()
    name = name.strip()
    if not name:
        return False, "Group name is required.", {}
        
    existing = db.groups.find_one({"user_id": user_id, "name": name})
    if existing:
        return False, f"Group '{name}' already exists.", {}
        
    doc = {
        "user_id": user_id,
        "name": name,
        "description": description.strip(),
        "created_at": datetime.utcnow()
    }
    result = db.groups.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return True, "Group created successfully.", doc

def get_groups(user_id: str) -> list:
    """List all contact groups for user with contact count."""
    db = get_db()
    groups = list(db.groups.find({"user_id": user_id}).sort("name", 1))
    for g in groups:
        gid_str = str(g["_id"])
        g["_id"] = gid_str
        g["contact_count"] = db.contacts.count_documents({"user_id": user_id, "group_ids": gid_str})
    return groups

def delete_group(group_id: str, user_id: str) -> tuple[bool, str]:
    """Delete a contact group and unassign from contacts."""
    db = get_db()
    try:
        gid = ObjectId(group_id)
    except Exception:
        return False, "Invalid group ID."
    result = db.groups.delete_one({"_id": gid, "user_id": user_id})
    if result.deleted_count > 0:
        db.contacts.update_many({"user_id": user_id}, {"$pull": {"group_ids": group_id}})
        return True, "Group deleted."
    return False, "Group not found."

# Labels Management
def create_label(user_id: str, name: str, color: str = "#3b82f6") -> tuple[bool, str, dict]:
    """Create a label/tag."""
    db = get_db()
    name = name.strip()
    if not name:
        return False, "Label name is required.", {}
    existing = db.labels.find_one({"user_id": user_id, "name": name})
    if existing:
        return False, f"Label '{name}' already exists.", {}
        
    doc = {
        "user_id": user_id,
        "name": name,
        "color": color or "#3b82f6",
        "created_at": datetime.utcnow()
    }
    result = db.labels.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return True, "Label created successfully.", doc

def get_labels(user_id: str) -> list:
    """List all contact labels for user."""
    db = get_db()
    labels = list(db.labels.find({"user_id": user_id}).sort("name", 1))
    for l in labels:
        l["_id"] = str(l["_id"])
    return labels

def delete_label(label_id: str, user_id: str) -> tuple[bool, str]:
    """Delete a label and unassign from contacts."""
    db = get_db()
    try:
        lid = ObjectId(label_id)
    except Exception:
        return False, "Invalid label ID."
    result = db.labels.delete_one({"_id": lid, "user_id": user_id})
    if result.deleted_count > 0:
        db.contacts.update_many({"user_id": user_id}, {"$pull": {"label_ids": label_id}})
        return True, "Label deleted."
    return False, "Label not found."
