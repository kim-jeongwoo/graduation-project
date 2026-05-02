"""인증 API – 회원가입 / 로그인."""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import create_access_token
from app.event_store import add_event
from app.models.models import User
from app.schemas.schemas import AuthResponse, LoginRequest, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(plain: str) -> str:
    """bcrypt로 비밀번호를 해시합니다."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """해시된 비밀번호와 평문을 비교합니다."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DBSession = Depends(get_db)):
    # 이메일 중복 확인
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    user = User(
        email=body.email,
        password_hash=_hash_password(body.password),
        nickname=body.nickname,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.user_id)

    add_event("signup", user.nickname, user.email)

    return AuthResponse(
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname,
        token=token,
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    token = create_access_token(user.user_id)

    add_event("login", user.nickname, user.email)

    return AuthResponse(
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname,
        token=token,
    )
