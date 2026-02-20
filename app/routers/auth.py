"""
IDNA EdTech v7.3 — Authentication Router
PIN-based login for students and parents. JWT tokens.
Rate limited: 5 failed attempts = 15 min lockout.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES
from app.database import get_db
from app.models import Student, Parent, LoginAttempt

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    pin: str

class StudentLoginResponse(BaseModel):
    student_id: str
    name: str
    class_level: int
    token: str

class ParentLoginResponse(BaseModel):
    parent_id: str
    student_id: str
    name: str
    child_name: str
    token: str


# ─── JWT Helpers ─────────────────────────────────────────────────────────────

def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and verify JWT from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth[7:]
    return verify_token(token)


# ─── Rate Limiting ───────────────────────────────────────────────────────────

def _check_rate_limit(db: DBSession, pin: str, ip: str) -> None:
    """Check if this PIN is locked out due to failed attempts."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
    recent_failures = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.pin == pin,
            LoginAttempt.success == False,
            LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )
    if recent_failures >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes."
        )


def _log_attempt(db: DBSession, pin: str, success: bool, ip: str) -> None:
    attempt = LoginAttempt(pin=pin, success=success, ip_address=ip)
    db.add(attempt)
    db.commit()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/student", response_model=StudentLoginResponse)
def login_student(req: LoginRequest, request: Request, db: DBSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(db, req.pin, ip)

    student = db.query(Student).filter(Student.pin == req.pin).first()
    if not student:
        _log_attempt(db, req.pin, False, ip)
        raise HTTPException(status_code=401, detail="PIN galat hai")

    _log_attempt(db, req.pin, True, ip)
    token = create_token(student.id, "student")

    return StudentLoginResponse(
        student_id=student.id,
        name=student.name,
        class_level=student.class_level,
        token=token,
    )


@router.post("/parent", response_model=ParentLoginResponse)
def login_parent(req: LoginRequest, request: Request, db: DBSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(db, req.pin, ip)

    parent = db.query(Parent).filter(Parent.pin == req.pin).first()
    if not parent:
        _log_attempt(db, req.pin, False, ip)
        raise HTTPException(status_code=401, detail="PIN galat hai")

    _log_attempt(db, req.pin, True, ip)
    token = create_token(parent.id, "parent")

    return ParentLoginResponse(
        parent_id=parent.id,
        student_id=parent.student_id,
        name=parent.name,
        child_name=parent.student.name,
        token=token,
    )
