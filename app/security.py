import base64
import hashlib
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

def _get_fernet_key() -> bytes:
    """Generate a valid 32-byte Fernet key from configured ENCRYPTION_KEY or SECRET_KEY."""
    raw_key = Config.ENCRYPTION_KEY or Config.SECRET_KEY
    if not raw_key:
        raw_key = "default-fallback-key-32bytes-long"
    
    # Hash to 32 bytes and urlsafe base64 encode
    key_bytes = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)

_fernet = Fernet(_get_fernet_key())

def hash_password(password: str) -> str:
    """Hash password using Werkzeug's default pbkdf2:sha256 or scrypt method."""
    return generate_password_hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    """Verify password against hash."""
    return check_password_hash(password_hash, password)

def encrypt_credential(secret_text: str) -> str:
    """Encrypt sensitive string (e.g. Gmail App Password) using Fernet symmetric encryption."""
    if not secret_text:
        return ""
    encrypted_bytes = _fernet.encrypt(secret_text.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_credential(encrypted_text: str) -> str:
    """Decrypt sensitive string using Fernet key."""
    if not encrypted_text:
        return ""
    try:
        decrypted_bytes = _fernet.decrypt(encrypted_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"[Security Error] Decryption failed: {e}")
        return ""

def mask_password(secret_text: str) -> str:
    """Return masked string for UI display."""
    if not secret_text:
        return ""
    return "••••••••••••"
