from datetime import datetime
from bson import ObjectId
from flask import session
from app.db import get_db
from app.security import hash_password, verify_password

def register_user(username: str, email: str, password: str, full_name: str = "") -> tuple[bool, str, dict]:
    """Register a new application user."""
    db = get_db()
    username = username.strip().lower()
    email = email.strip().lower()
    
    if not username or not email or not password:
        return False, "Username, email, and password are required.", {}
        
    if db.users.find_one({"$or": [{"username": username}, {"email": email}]}):
        return False, "Username or email already exists.", {}
        
    user_doc = {
        "username": username,
        "email": email,
        "full_name": full_name or username.title(),
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.users.insert_one(user_doc)
    user_doc["_id"] = str(result.inserted_id)
    return True, "User registered successfully.", user_doc

def login_user(username_or_email: str, password: str) -> tuple[bool, str, dict]:
    """Authenticate user credentials and start session."""
    db = get_db()
    identifier = username_or_email.strip().lower()
    
    user = db.users.find_one({"$or": [{"username": identifier}, {"email": identifier}]})
    if not user:
        return False, "Invalid username/email or password.", {}
        
    if not verify_password(user.get("password_hash", ""), password):
        return False, "Invalid username/email or password.", {}
        
    session["user_id"] = str(user["_id"])
    session["username"] = user["username"]
    session["email"] = user["email"]
    session["full_name"] = user.get("full_name", user["username"])
    
    user["_id"] = str(user["_id"])
    return True, "Login successful.", user

def logout_user():
    """Clear session data."""
    session.clear()

def get_current_user():
    """Retrieve logged-in user from session or database."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    db = get_db()
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user
    except Exception:
        return None
