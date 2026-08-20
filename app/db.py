import os
from pymongo import MongoClient
from config import Config

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client[Config.MONGODB_DB_NAME]
