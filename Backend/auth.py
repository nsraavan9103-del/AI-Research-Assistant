from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Header
from database import SessionLocal
from models import User

SECRET = "secret123"
ALGORITHM = "HS256"

pwd = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# ---------- PASSWORD ----------

def hash_password(password: str) -> str:
    return pwd.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)

# ---------- TOKEN ----------

def create_token(data: dict):
    return jwt.encode(data, SECRET, algorithm=ALGORITHM)

# ---------- AUTH ----------

def get_current_user(token: str = Header(...)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        db.close()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
