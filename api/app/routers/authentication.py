from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models_community import Region, User
from app.schemas_community import TokenOut, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])


def _serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        nickname=user.nickname,
        region=user.region.name if user.region else None,
        level=user.level.name if user.level else None,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    nickname = payload.nickname.strip()
    if not nickname:
        raise HTTPException(status_code=422, detail="닉네임을 입력하세요")
    if db.query(User).filter(User.nickname == nickname).first():
        raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다")

    region = None
    if payload.region_slug:
        region = db.query(Region).filter(Region.slug == payload.region_slug).first()
        if not region:
            raise HTTPException(status_code=400, detail="존재하지 않는 지역입니다")
    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    user = User(nickname=nickname, password_hash=password_hash, region_id=region.id if region else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    token, expires_in = create_access_token(user)
    return TokenOut(access_token=token, expires_in=expires_in, user=_serialize_user(user))


@router.post("/token", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.nickname == form.username.strip()).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="닉네임 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user)
    return TokenOut(access_token=token, expires_in=expires_in, user=_serialize_user(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _serialize_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1
    db.commit()
