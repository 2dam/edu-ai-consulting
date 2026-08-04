from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_community import AdmissionVideo
from app.schemas_community import (
    AdmissionVideoFeedPage,
    AdmissionVideoIn,
    AdmissionVideoIngestResult,
    AdmissionVideoOut,
)


router = APIRouter(prefix="/videos", tags=["admission-videos"])


def _serialize(video: AdmissionVideo) -> AdmissionVideoOut:
    return AdmissionVideoOut(
        id=video.id,
        video_id=video.video_id,
        source_url=video.source_url,
        title=video.title,
        description=video.description,
        channel_id=video.channel_id,
        channel_title=video.channel_title,
        published_at=video.published_at,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        view_count=video.view_count,
        like_count=video.like_count,
        comment_count=video.comment_count,
        search_query=video.search_query,
        crawled_at=video.crawled_at,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


@router.get("/feed", response_model=AdmissionVideoFeedPage)
def get_video_feed(
    q: str | None = Query(default=None, max_length=100),
    search_query: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(AdmissionVideo)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(AdmissionVideo.title.ilike(term), AdmissionVideo.channel_title.ilike(term))
        )
    if search_query:
        query = query.filter(AdmissionVideo.search_query == search_query)

    total = query.count()
    videos = (
        query.order_by(AdmissionVideo.published_at.desc(), AdmissionVideo.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AdmissionVideoFeedPage(
        items=[_serialize(video) for video in videos],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/ingest-batch", response_model=AdmissionVideoIngestResult)
def ingest_video_batch(payloads: list[AdmissionVideoIn], db: Session = Depends(get_db)):
    if len(payloads) > 500:
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail="한 번에 최대 500건까지 저장할 수 있습니다.")

    unique_payloads: dict[str, AdmissionVideoIn] = {}
    for payload in payloads:
        # 같은 영상이 여러 검색어에 잡히면 마지막 수집 통계를 사용한다.
        unique_payloads[payload.video_id] = payload

    created = 0
    updated = 0
    for payload in unique_payloads.values():
        video = db.query(AdmissionVideo).filter(AdmissionVideo.video_id == payload.video_id).first()
        if video is None:
            video = AdmissionVideo(video_id=payload.video_id)
            db.add(video)
            created += 1
        else:
            updated += 1

        for field, value in payload.model_dump(exclude={"platform"}).items():
            setattr(video, field, value)

    db.commit()
    return AdmissionVideoIngestResult(
        total=len(payloads),
        unique=len(unique_payloads),
        duplicates=len(payloads) - len(unique_payloads),
        created=created,
        updated=updated,
    )
