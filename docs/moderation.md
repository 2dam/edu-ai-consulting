# 모더레이션 정책

## 기본 원칙

- **개인정보 노출 금지**: 신고 사유(`reason`)에 `personal_info`가 명시적으로 포함되어
  있으며, 크롤러의 `AnonymizePipeline`이 학생 실명/연락처 등 PII 필드를 수집 단계에서
  제거합니다.
- **신고 버튼**: 모든 게시글(커뮤니티/뉴스)에 신고 버튼이 있으며, 로그인(임시 인증)한
  사용자는 누구나 신고할 수 있습니다.
- **관리자 숨김/삭제**: 관리자만 콘텐츠의 노출 여부를 바꿀 수 있고, 모든 조치는
  `ModerationLog`에 기록됩니다.
- **독성 댓글 탐지는 advisory(참고용)일 뿐**: AI가 댓글을 부적절하다고 판단해도
  `toxicity_flag`만 세팅될 뿐 자동으로 숨기거나 삭제하지 않습니다. 최종 판단은 항상
  사람(관리자)이 합니다.
- **가짜뉴스 위험도는 확정적 판단이 아님**: `NewsPost.fake_news_risk_label`은 참고용
  라벨이며, 뉴스 콘텐츠에는 항상 원문 출처 URL(`source_url`)을 함께 노출해 사용자가
  직접 판단할 수 있게 합니다 (프론트엔드 `SourceLink` 컴포넌트가 이를 항상 렌더링).

## 모더레이션 상태 라이프사이클

`ModerationStatus`: `visible → hidden → deleted` (관리자가 `restore`로 다시 `visible`로
되돌릴 수 있음 — 현재는 `PATCH .../moderation`에 `visible`을 다시 지정하는 방식으로 처리).

`ReportStatus`: `open → reviewing → actioned | dismissed`

- 누구나 신고를 생성하면 `open` 상태로 시작합니다. (같은 대상에 대한 중복 신고는 막지
  않습니다 — 심각한 콘텐츠에 신고가 몰리는 것 자체가 신호이므로 의도적으로 허용)
- 관리자만 `PATCH /admin/community/posts/{id}/moderation` 또는
  `PATCH /admin/news/posts/{id}/moderation`을 호출할 수 있습니다
  (`api/app/auth.py`의 `require_admin` 의존성).
- 요청에 `related_report_id`를 포함하면 해당 신고가 자동으로 `actioned`로 바뀝니다.
- 댓글 단위 모더레이션(개별 댓글 숨김/삭제)은 아직 구현되지 않았습니다 — 관리자 신고
  큐에서 `target_type: "comment"`인 항목은 "아직 지원되지 않습니다"라는 안내만 표시됩니다
  (TODO).

## 관리자 권한

`api/app/auth.py`의 `ADMIN_USER_IDS`(현재 `{1}`으로 하드코딩)에 포함된 `user_id`만
관리자 라우트를 호출할 수 있습니다. 이는 **임시 조치**이며, 실제 서비스 전에 반드시
`User` 테이블에 `is_admin` 컬럼 또는 별도 역할(role) 테이블을 추가해 교체해야 합니다.
