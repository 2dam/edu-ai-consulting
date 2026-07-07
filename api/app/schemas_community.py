"""커뮤니티/뉴스/맘카페 모듈의 Pydantic 스키마. 기존 app.schemas의 flat 스타일을 그대로 따른다."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TargetTypeLit = Literal["post", "news_post", "comment"]
ReasonLit = Literal["spam", "abuse", "personal_info", "fake_news", "other"]
ModerationStatusLit = Literal["visible", "hidden", "deleted"]


# ---- 사용자 (임시 가입) ----
class UserCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=64)
    region_slug: str | None = None


class UserOut(BaseModel):
    id: int
    nickname: str
    region: str | None = None
    level: str | None = None
    created_at: datetime


# ---- 게시판 ----
class BoardOut(BaseModel):
    id: int
    slug: str
    name: str
    board_type: str
    region: str | None = None


# ---- 커뮤니티 게시글 ----
class CommunityPostCreate(BaseModel):
    board_slug: str
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class CommunityPostOut(BaseModel):
    id: int
    kind: Literal["post"] = "post"
    board_slug: str
    author_nickname: str
    title: str
    body: str
    upvote_count: int
    downvote_count: int
    comment_count: int
    moderation_status: str
    created_at: datetime


class CommentOut(BaseModel):
    id: int
    author_nickname: str
    body: str
    parent_id: int | None
    upvote_count: int
    downvote_count: int
    toxicity_flag: bool
    moderation_status: str
    created_at: datetime
    replies: list["CommentOut"] = []


CommentOut.model_rebuild()


class CommunityPostDetail(CommunityPostOut):
    comments: list[CommentOut] = []


class FeedPage(BaseModel):
    items: list[CommunityPostOut]
    total: int
    limit: int
    offset: int


# ---- 댓글 작성 ----
class CommentCreate(BaseModel):
    body: str = Field(min_length=1)
    parent_id: int | None = None


# ---- 투표 ----
class VoteRequest(BaseModel):
    value: Literal[1, -1]


class VoteResult(BaseModel):
    upvote_count: int
    downvote_count: int
    user_vote: Literal[1, -1, 0]


# ---- 신고 ----
class ReportCreate(BaseModel):
    reason: ReasonLit
    detail: str | None = None


class ReportOut(BaseModel):
    id: int
    target_type: TargetTypeLit
    target_id: int
    reason: str
    detail: str | None
    status: str
    created_at: datetime


class ReportQueueItem(ReportOut):
    target_preview: str


# ---- 뉴스 ----
class NewsImportRequest(BaseModel):
    url: str
    title: str
    source_name: str | None = None
    category: str | None = None
    body_text: str | None = None
    thumbnail_url: str | None = None
    region_slug: str | None = None
    published_at: datetime | None = None
    tags: list[str] = []


class NewsPostOut(BaseModel):
    id: int
    kind: Literal["news_post"] = "news_post"
    title: str
    source_url: str
    source_name: str | None
    category: str | None
    thumbnail_url: str | None
    region: str | None = None
    tags: list[str] = []
    fake_news_risk_label: str | None
    published_at: datetime | None
    upvote_count: int
    downvote_count: int
    comment_count: int
    moderation_status: str
    created_at: datetime


class NewsPostDetail(NewsPostOut):
    body_text: str | None = None
    comments: list[CommentOut] = []


class NewsFeedPage(BaseModel):
    items: list[NewsPostOut]
    total: int
    limit: int
    offset: int


class NewsSummaryOut(BaseModel):
    news_post_id: int
    summary: str
    model_name: str


# ---- 토론 요약 / 관련 게시글 (부가 AI 기능) ----
class DebateSummaryOut(BaseModel):
    news_post_id: int
    comment_summary: str
    agree: list[str]
    disagree: list[str]


class RelatedPostOut(BaseModel):
    id: int
    title: str


# ---- Admin ----
class ModerationPatch(BaseModel):
    moderation_status: ModerationStatusLit
    reason: str | None = None
    related_report_id: int | None = None
