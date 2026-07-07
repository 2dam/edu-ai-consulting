/**
 * 백엔드는 UTC로 시각을 저장하지만(app.database의 datetime.now(timezone.utc)), SQLite는
 * timezone-aware DateTime을 지원하지 않아 왕복 후 오프셋 없는 naive 문자열로 직렬화된다
 * (예: "2026-07-07T02:44:22" — 뒤에 Z/+00:00 없음). 오프셋이 없으면 브라우저는 이를
 * 로컬 시간대로 해석해버려 KST(UTC+9) 환경에서 모든 시각이 9시간 어긋난다.
 * 그래서 API에서 온 날짜 문자열은 항상 이 함수를 통해서만 Date로 변환한다.
 */
export function parseApiDate(iso: string): Date {
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(iso);
  return new Date(hasOffset ? iso : `${iso}Z`);
}
