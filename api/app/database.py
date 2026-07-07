import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edu_consulting.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# SQLite는 동시 쓰기가 1개뿐이라, 커뮤니티 기능(투표·댓글 등)으로 요청이 몰리면
# 파일 잠금 대기가 길어져 커넥션 풀이 고갈되고 QueuePool timeout으로 이어질 수 있다.
# timeout으로 sqlite3 자체의 잠금 대기를, WAL로 읽기/쓰기 동시성을 개선한다.
connect_args = {"check_same_thread": False, "timeout": 15} if IS_SQLITE else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

if IS_SQLITE:
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
