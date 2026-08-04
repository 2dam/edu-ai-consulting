"""OAuth2 Bearer/JWT authentication for the community API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_community import User

PBKDF2_ITERATIONS = 600_000
ACCESS_TOKEN_SECONDS = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "60")) * 60
JWT_ISSUER = os.getenv("JWT_ISSUER", "edu-ai-consulting")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "edu-ai-community")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _jwt_secret() -> bytes:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be set to at least 32 characters")
    return secret.encode("utf-8")


def validate_auth_configuration() -> None:
    """Fail fast instead of creating accounts that cannot receive a token."""
    _jwt_secret()


def hash_password(password: str) -> str:
    if len(password) < 10 or len(password) > 128:
        raise ValueError("비밀번호는 10자 이상 128자 이하여야 합니다")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(_b64encode(digest), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> tuple[str, int]:
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + ACCESS_TOKEN_SECONDS,
        "jti": secrets.token_urlsafe(16),
        "ver": user.token_version,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded = ".".join(
        (_b64encode(json.dumps(header, separators=(",", ":")).encode()),
         _b64encode(json.dumps(payload, separators=(",", ":")).encode()))
    )
    signature = hmac.new(_jwt_secret(), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}", ACCESS_TOKEN_SECONDS


def decode_access_token(token: str) -> dict:
    unauthorized = HTTPException(
        status_code=401,
        detail="유효하지 않거나 만료된 인증 토큰입니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signed = f"{encoded_header}.{encoded_payload}"
        expected = hmac.new(_jwt_secret(), signed.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(encoded_signature)):
            raise unauthorized
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
        now = int(time.time())
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise unauthorized
        if payload.get("iss") != JWT_ISSUER or payload.get("aud") != JWT_AUDIENCE:
            raise unauthorized
        if not isinstance(payload.get("exp"), int) or payload["exp"] <= now:
            raise unauthorized
        if not isinstance(payload.get("iat"), int) or payload["iat"] > now + 60:
            raise unauthorized
        int(payload["sub"])
        return payload
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise unauthorized


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    user = db.get(User, int(payload["sub"]))
    if not user or user.password_hash is None or payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=401,
            detail="로그인이 만료되었습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return user
