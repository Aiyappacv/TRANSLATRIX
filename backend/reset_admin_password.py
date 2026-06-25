"""Reset admin password to known value"""
from app.database import engine
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD = "SecurePass123!"
EMAIL = "admin@translatrix.com"

hashed = pwd_context.hash(PASSWORD)

with engine.connect() as conn:
    result = conn.execute(
        text("UPDATE users SET hashed_password = :pwd WHERE email = :email"),
        {"pwd": hashed, "email": EMAIL}
    )
    conn.commit()
    print(f"[SUCCESS] Password reset for {EMAIL}")
    print(f"New password: {PASSWORD}")
