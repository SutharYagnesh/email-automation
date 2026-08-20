import os
from pymongo import MongoClient, ASCENDING
from config import Config

class Database:
    client = None
    db = None

def init_db(app=None):
    """Initialize PyMongo client and create database indexes."""
    if Database.db is not None:
        return Database.db
        
    uri = Config.MONGODB_URI
    db_name = Config.MONGODB_DB_NAME
    
    try:
        Database.client = MongoClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
        Database.db = Database.client[db_name]
    except Exception as e:
        print(f"[Database Error] Connection failed: {e}")
        # Try fallback MongoClient without extra params if initial attempt fails
        Database.client = MongoClient(uri)
        Database.db = Database.client[db_name]
    
    # Create indexes for optimal performance and constraint enforcement
    try:
        # Users
        Database.db.users.create_index([("username", ASCENDING)], unique=True)
        Database.db.users.create_index([("email", ASCENDING)], unique=True)
        
        # Contacts (prevent duplicate emails per user)
        Database.db.contacts.create_index([("user_id", ASCENDING), ("email", ASCENDING)], unique=True)
        Database.db.contacts.create_index([("user_id", ASCENDING), ("group_ids", ASCENDING)])
        
        # Contact Groups
        Database.db.groups.create_index([("user_id", ASCENDING), ("name", ASCENDING)], unique=True)
        
        # Contact Labels
        Database.db.labels.create_index([("user_id", ASCENDING), ("name", ASCENDING)], unique=True)
        
        # Sender Accounts
        Database.db.sender_accounts.create_index([("user_id", ASCENDING), ("username", ASCENDING)], unique=True)
        
        # Templates
        Database.db.templates.create_index([("user_id", ASCENDING)])
        
        # Campaigns
        Database.db.campaigns.create_index([("user_id", ASCENDING)])
        Database.db.campaigns.create_index([("status", ASCENDING)])
        
        # Sent Emails
        Database.db.sent_emails.create_index([("campaign_id", ASCENDING)])
        Database.db.sent_emails.create_index([("user_id", ASCENDING)])
        Database.db.sent_emails.create_index([("recipient_email", ASCENDING)])
        Database.db.sent_emails.create_index([("tracking_id", ASCENDING)], unique=True, sparse=True)
        Database.db.sent_emails.create_index([("message_id", ASCENDING)])
        
        # Tracking Events
        Database.db.tracking_events.create_index([("sent_email_id", ASCENDING)])
        Database.db.tracking_events.create_index([("campaign_id", ASCENDING)])
        
        print(f"[Database] Connected successfully to MongoDB: {db_name}")
    except Exception as e:
        print(f"[Database] Warning during index creation: {e}")

def get_db():
    """Get MongoDB database instance."""
    if Database.db is None:
        res = init_db()
        if res is None and Database.db is None:
            # Fallback direct connection attempt
            try:
                uri = Config.MONGODB_URI
                db_name = Config.MONGODB_DB_NAME
                Database.client = MongoClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
                Database.db = Database.client[db_name]
            except Exception as e:
                raise RuntimeError(f"Failed to connect to MongoDB: {e}")
    return Database.db
