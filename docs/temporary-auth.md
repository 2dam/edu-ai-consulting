# OAuth2/JWT 인증

기존 `X-User-Id` 헤더 방식은 누구나 다른 사용자 ID를 넣을 수 있는 스푸핑 취약점 때문에
폐기되었습니다. 현재 쓰기 요청과 관리자 API는 OAuth2 Bearer JWT만 허용합니다.

## API 흐름

1. `POST /auth/register`에 `nickname`, `password`, 선택적인 `region_slug`를 보냅니다.
2. 로그인은 `POST /auth/token`에 OAuth2 form 형식의 `username`, `password`를 보냅니다.
3. 응답의 `access_token`을 `Authorization: Bearer <token>` 헤더로 전달합니다.
4. `GET /auth/me`로 현재 사용자를 복원하고 `POST /auth/logout`으로 해당 사용자의 기존
   토큰을 모두 무효화합니다.

비밀번호는 원문으로 저장하지 않고 무작위 salt와 PBKDF2-SHA256 600,000회 반복으로
해시합니다. JWT는 HS256 서명, 발급자·대상·발급시각·만료시각·토큰 버전을 검증합니다.

## 필수 운영 설정

- `JWT_SECRET_KEY`: 32자 이상의 무작위 비밀값. 소스 저장소에 커밋하지 않습니다.
- `JWT_ACCESS_TOKEN_MINUTES`: 액세스 토큰 만료시간(기본 60분).
- `ADMIN_PASSWORD`: 기존 관리자(id=1)에 비밀번호가 없을 때 최초 한 번만 설정합니다.
  해시가 DB에 저장된 것을 확인한 뒤 환경변수에서 제거합니다.

기존 DB는 서버 기동 시 `password_hash`, `is_admin`, `token_version` 컬럼을 데이터 손실 없이
추가합니다. 기존 임시 사용자는 비밀번호 해시가 없어 로그인할 수 없으므로 별도의 계정 복구
또는 재가입 안내가 필요합니다.

## 남은 보안 운영 작업

- 로그인·회원가입 rate limiting 및 반복 실패 잠금
- 이메일/휴대전화 검증과 비밀번호 재설정
- 여러 기기별 refresh token 회전 및 세션 목록
- 비밀값 관리 서비스와 정기적인 키 교체
- 보안 이벤트 감사 로그와 이상 로그인 알림
