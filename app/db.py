import os
from pymongo import MongoClient
from config import Config

_client = None

def get_db():
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=200000,
                tlsAllowInvalidCertificates=True
            )
        except Exception:
            _client = MongoClient(Config.MONGODB_URI)
    return _client[Config.MONGODB_DB_NAME]
