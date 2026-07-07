# 커뮤니티/뉴스/맘카페 데이터 모델

"AI 교육 뉴스 커뮤니티 + 학부모 맘카페 + 지역 교육정보 플랫폼" 모듈의 DB 스키마 설명.
모든 모델은 `api/app/models_community.py`에 정의되어 있으며, 기존 `api/app/models.py`
(`RawRecord`, `ConsultingReport`)와 같은 SQLite DB, 같은 SQLAlchemy `Base`를 공유합니다.

## 테이블 관계

```
Region (시/도 17개, 시드 데이터)
  └─ Board (게시판: general/education/parenting/region/news)
       ├─ CommunityPost (board_id 필수)
       └─ NewsPost (board_id 선택, region_id 선택)

User (임시 가입 — 닉네임만, 비밀번호 없음)
  ├─ CommunityPost.author_id
  ├─ Comment.author_id
  ├─ Vote.user_id
  └─ Report.reporter_id

Comment (target_type + target_id로 CommunityPost 또는 NewsPost를 가리킴)
  └─ parent_id (자기참조 — 무한 depth 대댓글)

Vote / Report / AISummary / ModerationLog
  └─ target_type + target_id 판별 컬럼으로 post/news_post/comment를 폴리모픽하게 참조
```

## 왜 Board가 enum이 아니라 테이블인가

- 관리자가 배포 없이 게시판을 추가/변경할 수 있어야 함
- `GET /mom-cafe/boards`가 이름/설명 등 메타데이터를 나열해야 함
- 지역 게시판 17개를 하드코딩하지 않고 `Region`과 1:1로 데이터 기반 생성 가능

`Board.board_type`은 `general`/`education`/`parenting`/`region`/`news` 중 하나이며,
API 라우팅에서 어떤 종류의 게시판인지 구분하는 용도로만 쓰입니다. `board_type == region`일
때만 `region_id`가 채워집니다.

## 왜 Vote/Report/Comment가 폴리모픽 target_type + target_id 패턴인가

Post용/Comment용 Vote 테이블을 따로 두는 대신, `target_type`(`post`/`news_post`/`comment`)
+ `target_id` 판별 컬럼을 가진 테이블 하나로 통일했습니다.

- 투표/신고는 대상이 무엇이든 모양(사용자, 값/사유, 시각, 중복 방지)이 동일함
- admin 신고함이 테이블 하나로 통합되어 페이지네이션·필터링이 단순해짐
- 새 투표/신고 가능 엔티티가 늘어나도 매번 테이블을 추가하지 않아도 됨

트레이드오프: DB 레벨 FK 무결성은 없고, 앱 레벨에서 `target_type` enum 값만 검증합니다
(MVP 규모에서는 허용 가능한 수준으로 판단).

`Vote`에는 `(user_id, target_type, target_id)` 유니크 제약이 걸려 있어 중복 투표를
막습니다 — 같은 값으로 재투표하면 투표가 취소되고, 반대 값으로 투표하면 전환됩니다
(`api/app/community_common.py`의 `apply_vote` 참고).

## AISummary / ModerationLog

- `AISummary`: `summary_type`(`news_summary`/`debate_summary`)별로 AI 생성 결과를 캐싱해
  같은 뉴스 기사에 대해 OpenAI를 반복 호출하지 않도록 함. `content`는 요약 텍스트 또는
  JSON 문자열(`debate_summary`의 찬성/반대 목록 포함).
- `ModerationLog`: 관리자가 게시글/뉴스를 숨기거나 삭제할 때마다 한 행씩 남는 감사 로그.
  `related_report_id`가 있으면 해당 신고를 처리한 조치임을 의미합니다.

## 시드 데이터

`api/app/seed.py`의 `seed_defaults()`가 FastAPI startup 시점에 호출되어, `Region`/`Board`
테이블이 비어있을 때만 한국 시/도 17개와 기본 게시판(자유/교육/육아/뉴스 + 지역별)을
채웁니다. 멱등이므로 여러 번 재시작해도 중복 삽입되지 않습니다.
