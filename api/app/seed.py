"""로컬 개발 편의를 위한 멱등 시드 함수.

Region/Board 테이블이 비어있을 때만 기본 지역(한국 시/도 17개)과 기본 게시판
(자유/교육/육아/뉴스 + 지역별 게시판)을 채운다. main.py의 FastAPI startup 이벤트에서
호출되며, 별도 마이그레이션 도구 없이 새 SQLite DB에서 바로 개발을 시작할 수 있게 한다.

관리자 유저(id=1)도 여기서 함께 보장하고 DB의 is_admin 권한을 설정한다. 최초 비밀번호는
ADMIN_PASSWORD 환경변수가 있을 때만 해시해 저장한다.
"""
import os

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models_community import Board, BoardType, Region, User

REGIONS = [
    ("서울", "seoul"),
    ("부산", "busan"),
    ("대구", "daegu"),
    ("인천", "incheon"),
    ("광주", "gwangju"),
    ("대전", "daejeon"),
    ("울산", "ulsan"),
    ("세종", "sejong"),
    ("경기", "gyeonggi"),
    ("강원", "gangwon"),
    ("충북", "chungbuk"),
    ("충남", "chungnam"),
    ("전북", "jeonbuk"),
    ("전남", "jeonnam"),
    ("경북", "gyeongbuk"),
    ("경남", "gyeongnam"),
    ("제주", "jeju"),
]

DEFAULT_BOARDS = [
    ("general", "자유게시판", BoardType.GENERAL),
    ("education", "교육 게시판", BoardType.EDUCATION),
    ("parenting", "육아 게시판", BoardType.PARENTING),
    ("news", "뉴스 게시판", BoardType.NEWS),
]


def migrate_auth_schema(db: Session) -> None:
    """기존 users 테이블에 인증 컬럼을 데이터 손실 없이 추가한다."""
    columns = {c["name"] for c in inspect(db.bind).get_columns("users")}
    additions = {
        "password_hash": "VARCHAR(255)",
        "is_admin": "BOOLEAN NOT NULL DEFAULT FALSE",
        "token_version": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in additions.items():
        if name not in columns:
            db.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
    db.commit()


def seed_defaults(db: Session) -> None:
    if db.query(Region).first() is None:
        for name, slug in REGIONS:
            db.add(Region(name=name, slug=slug))
        db.commit()

    if db.query(Board).first() is None:
        for slug, name, board_type in DEFAULT_BOARDS:
            db.add(Board(slug=slug, name=name, board_type=board_type))

        regions = {r.slug: r for r in db.query(Region).all()}
        for _, slug in REGIONS:
            region = regions[slug]
            db.add(
                Board(
                    slug=f"region-{slug}",
                    name=f"{region.name} 지역 게시판",
                    board_type=BoardType.REGION,
                    region_id=region.id,
                )
            )
        db.commit()

    admin = db.get(User, 1)
    if admin is None:
        nickname = "admin"
        suffix = 1
        while db.query(User).filter(User.nickname == nickname).first() is not None:
            suffix += 1
            nickname = f"admin{suffix}"
        admin = User(id=1, nickname=nickname, is_admin=True)
        db.add(admin)
        db.commit()
    elif not admin.is_admin:
        admin.is_admin = True
        db.commit()

    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_password and not admin.password_hash:
        admin.password_hash = hash_password(admin_password)
        db.commit()
