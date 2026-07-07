"""임시 인증.

TODO: replace with real OAuth2/JWT auth. 지금은 비밀번호/세션이 전혀 없다.
클라이언트는 POST /community/users 로 닉네임만으로 "가입"해 user_id를 발급받고,
이후 모든 쓰기 요청에 X-User-Id 헤더로 그 id를 실어 보낸다. 헤더 값은 그대로
신뢰하므로 스푸핑 가능 — 프로덕션 전환 시 반드시 실제 인증으로 교체해야 한다
(docs/temporary-auth.md 참고).
"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_community import User

# TODO: 진짜 role/is_admin 컬럼(또는 별도 권한 테이블)으로 교체.
# 지금은 이 집합에 포함된 user_id만 admin 라우트를 호출할 수 있다.
ADMIN_USER_IDS: set[int] = {1}


def get_current_user(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="X-User-Id 헤더가 필요합니다 (임시 인증, POST /community/users로 발급)")
    user = db.get(User, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.id not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return user
