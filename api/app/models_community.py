"""
"AI 교육 뉴스 커뮤니티 + 학부모 맘카페 + 지역 교육정보 플랫폼" 모듈의 DB 모델.

기존 app.models (RawRecord/ConsultingReport)와 별개 파일로 분리하되 같은 Base/engine을
공유한다. main.py에서 이 모듈을 import하기만 하면 Base.metadata.create_all()이
아래 테이블을 모두 인식한다.

폴리모픽 대상(Vote/Report/AISummary/Comment의 부모)은 별도 테이블 대신
target_type + target_id 판별 컬럼 패턴 하나로 통일했다. DB 레벨 FK 무결성은
포기하지만(대신 라우터에서 target_type 값을 검증), 신규 대상 타입이 늘어날 때마다
테이블을 추가하지 않아도 되고 admin 신고함/투표 로직이 한 곳으로 모인다.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TargetType(str, enum.Enum):
    POST = "post"
    NEWS_POST = "news_post"
    COMMENT = "comment"


class ModerationStatus(str, enum.Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    DELETED = "deleted"


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    REVIEWING = "reviewing"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class BoardType(str, enum.Enum):
    GENERAL = "general"
    EDUCATION = "education"
    PARENTING = "parenting"
    REGION = "region"
    NEWS = "news"


class UserLevel(Base):
    """활동 등급 (게시글/댓글 활동량에 따른 뱃지 성격 — 승급 로직은 추후 배치잡으로 구현)."""

    __tablename__ = "user_levels"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)  # "새싹회원", "우수회원" 등
    min_points = Column(Integer, default=0, nullable=False)


class Region(Base):
    """한국 시/도 단위 지역 (지역 게시판 및 뉴스 지역 태깅에 사용)."""

    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False, unique=True)  # "서울", "광주" 등
    slug = Column(String(32), nullable=False, unique=True)  # /mom-cafe/region/{slug}


class User(Base):
    """임시 사용자 모델.

    TODO: replace with real OAuth2/JWT auth. 지금은 비밀번호/세션이 전혀 없고
    닉네임만으로 가입하며, 클라이언트가 발급받은 id를 X-User-Id 헤더로 보내는
    방식으로만 신원을 구분한다 (app/auth.py 참고).
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String(64), nullable=False, unique=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    level_id = Column(Integer, ForeignKey("user_levels.id"), nullable=True)
    created_at = Column(DateTime, default=_now)

    region = relationship("Region")
    level = relationship("UserLevel")


class Board(Base):
    """게시판 — enum이 아니라 실제 테이블. admin이 배포 없이 게시판을 추가/변경할 수 있고,
    /mom-cafe/boards가 메타데이터를 나열할 수 있어야 하며, 지역 게시판은 Region과
    1:1로 데이터 기반 생성이 가능해야 하기 때문."""

    __tablename__ = "boards"

    id = Column(Integer, primary_key=True)
    slug = Column(String(64), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    board_type = Column(Enum(BoardType), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)

    region = relationship("Region")


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    upvote_count = Column(Integer, default=0, nullable=False)
    downvote_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    moderation_status = Column(
        Enum(ModerationStatus), default=ModerationStatus.VISIBLE, nullable=False, index=True
    )
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    board = relationship("Board")
    author = relationship("User")


class NewsPost(Base):
    """크롤러(education_news_spider) 또는 관리자 수동 등록(/news/import-url)으로 들어오는 뉴스 기사.

    RawRecord(JSON blob 범용 저장소)와 별도의 전용 테이블로 둔 이유: 뉴스는 실시간
    피드/투표/댓글/지역 필터링이 필요한 1급 엔티티라 실제 컬럼과 인덱스가 필요하다.
    """

    __tablename__ = "news_posts"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    title = Column(String(255), nullable=False)
    source_url = Column(String(512), nullable=False)  # 안전 요구사항: 항상 출처 표시
    source_name = Column(String(128), nullable=True)
    category = Column(String(64), nullable=True)
    body_text = Column(Text, nullable=True)
    thumbnail_url = Column(String(512), nullable=True)
    tags = Column(String(255), nullable=True)  # comma-separated (MVP 단계 — 필요 시 연관 테이블로 이관)
    published_at = Column(DateTime, nullable=True)
    # 가짜뉴스 위험도는 어디까지나 참고용(advisory)이며 자동 숨김/삭제의 근거가 되지 않는다.
    fake_news_risk_label = Column(String(16), nullable=True)
    upvote_count = Column(Integer, default=0, nullable=False)
    downvote_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    moderation_status = Column(
        Enum(ModerationStatus), default=ModerationStatus.VISIBLE, nullable=False, index=True
    )
    created_at = Column(DateTime, default=_now)

    board = relationship("Board")
    region = relationship("Region")


class Comment(Base):
    """댓글/대댓글. target_type+target_id로 CommunityPost 또는 NewsPost 어디에든 달릴 수 있고,
    parent_id 자기참조로 무한 depth 대댓글을 표현한다."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    upvote_count = Column(Integer, default=0, nullable=False)
    downvote_count = Column(Integer, default=0, nullable=False)
    moderation_status = Column(
        Enum(ModerationStatus), default=ModerationStatus.VISIBLE, nullable=False, index=True
    )
    # AI 독성 탐지 결과 — advisory 플래그일 뿐, 자동으로 숨기거나 삭제하지 않는다.
    toxicity_flag = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)

    author = relationship("User")
    replies = relationship(
        "Comment",
        backref=backref("parent", remote_side=[id]),
        order_by="Comment.created_at",
    )

    __table_args__ = (Index("ix_comments_target", "target_type", "target_id"),)


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)
    value = Column(Integer, nullable=False)  # +1 / -1
    created_at = Column(DateTime, default=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_vote_user_target"),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(64), nullable=False)  # spam/abuse/personal_info/fake_news/other
    detail = Column(Text, nullable=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.OPEN, nullable=False, index=True)
    created_at = Column(DateTime, default=_now)


class AISummary(Base):
    """뉴스 요약 / 댓글 스레드 요약 / 토론 쟁점 추출 결과를 캐싱해 OpenAI 재호출 비용을 줄인다."""

    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True)
    summary_type = Column(String(32), nullable=False)  # news_summary/comment_thread_summary/debate_points
    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)  # summary_type에 따라 plain text 또는 JSON 문자열
    model_name = Column(String(64), default="gpt-4o-mini")
    created_at = Column(DateTime, default=_now)


class ModerationLog(Base):
    """admin 모더레이션 조치 감사 로그."""

    __tablename__ = "moderation_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_type = Column(Enum(TargetType), nullable=False)
    target_id = Column(Integer, nullable=False)
    action = Column(String(32), nullable=False)  # hide/delete/restore/dismiss_report/resolve_report
    reason = Column(Text, nullable=True)
    related_report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    created_at = Column(DateTime, default=_now)
