"""
Security Utilities
Password hashing, verification, and encryption
"""
import bcrypt
from cryptography.fernet import Fernet
from app.config import settings

# Using bcrypt directly to avoid passlib compatibility issues
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Bcrypt has a 72 byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hashed password

    Returns:
        True if password matches, False otherwise
    """
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Alias for hash_password for backward compatibility"""
    return hash_password(password)


# Encryption for sensitive data (like SAP credentials)
def get_cipher():
    """Get Fernet cipher instance using SECRET_KEY"""
    key = settings.SECRET_KEY[:32].encode().ljust(32, b'=')
    # Convert to base64 URL-safe format required by Fernet
    import base64
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value

    Args:
        value: Plain text value to encrypt

    Returns:
        Encrypted value as string
    """
    cipher = get_cipher()
    encrypted = cipher.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted string value

    Args:
        encrypted_value: Encrypted value

    Returns:
        Decrypted plain text value
    """
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_value.encode())
    return decrypted.decode()


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets minimum security requirements

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"

    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    return True, ""
