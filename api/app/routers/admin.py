from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.community_common import get_target_row, preview_text
from app.database import get_db
from app.models_community import (
    Comment,
    CommunityPost,
    ModerationLog,
    ModerationStatus,
    NewsPost,
    Report,
    ReportStatus,
    TargetType,
    User,
)
from app.schemas_community import ModerationPatch, ReportQueueItem

router = APIRouter(prefix="/admin", tags=["admin"])


def _target_preview(db: Session, target_type: TargetType, target_id: int) -> str:
    target = get_target_row(db, target_type, target_id)
    if target is None:
        return "(삭제되었거나 존재하지 않는 대상)"
    if isinstance(target, (CommunityPost, NewsPost)):
        return preview_text(target.title)
    if isinstance(target, Comment):
        return preview_text(target.body)
    return ""


@router.get("/community/reports", response_model=list[ReportQueueItem])
def list_reports(status: str = "open", admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(Report)
    if status != "all":
        try:
            query = query.filter(Report.status == ReportStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 status 값입니다")

    reports = query.order_by(Report.created_at.desc()).all()
    return [
        ReportQueueItem(
            id=r.id, target_type=r.target_type.value, target_id=r.target_id, reason=r.reason,
            detail=r.detail, status=r.status.value, created_at=r.created_at,
            target_preview=_target_preview(db, r.target_type, r.target_id),
        )
        for r in reports
    ]


def _apply_moderation(db: Session, admin: User, target, target_type: TargetType, payload: ModerationPatch):
    target.moderation_status = ModerationStatus(payload.moderation_status)
    db.add(
        ModerationLog(
            admin_id=admin.id, target_type=target_type, target_id=target.id,
            action=payload.moderation_status, reason=payload.reason,
            related_report_id=payload.related_report_id,
        )
    )
    if payload.related_report_id is not None:
        report = db.get(Report, payload.related_report_id)
        if report:
            report.status = ReportStatus.ACTIONED
    db.commit()


@router.patch("/community/posts/{post_id}/moderation")
def moderate_post(
    post_id: int, payload: ModerationPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    post = db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

    _apply_moderation(db, admin, post, TargetType.POST, payload)
    return {"id": post.id, "moderation_status": post.moderation_status.value}


@router.patch("/news/posts/{news_id}/moderation")
def moderate_news(
    news_id: int, payload: ModerationPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    news = db.get(NewsPost, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

    _apply_moderation(db, admin, news, TargetType.NEWS_POST, payload)
    return {"id": news.id, "moderation_status": news.moderation_status.value}
