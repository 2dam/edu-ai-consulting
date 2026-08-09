# buzz/ — EduIntel 내부 HQ (Buzz 릴레이)

`buzz.ichapterwise.com` 에 띄우는 Buzz 릴레이(내부 협업 워크스페이스) 설정 모음.
대외 플랫폼(ichapterwise.com)과 별도. 팀(창업자 1명) + AI 직원 6명 이 여기서 일함.

## 구성
- `Dockerfile` — Render 배포용 Buzz 이미지 래퍼
- `render-env.example` — Render Environment 변수 예시 (secret 은 대시보드에서)
- `agents.md` — AI 직원 6명 정의 (실제 API 엔드포인트 매핑)
- `workflows.yaml` — Buzz 워크플로 3개 (뉴스/리포트/모더레이션)
- `dns-setup.md` — buzz.ichapterwise.com DNS/Custom Domain 절차
- `identity.md` — npub/nsec 키 관리 (아동 PII Strict)

## 배포 흐름
1. `render.yaml` 에 `edu-ai-consulting-buzz` 서비스 이미 정의됨 (이 repo 루트)
2. Render 대시보드에서 secret 값 입력 (BUZZ_RELAY_PRIVATE_KEY 등)
3. `buzz/dns-setup.md` 따라 `buzz.ichapterwise.com` Custom Domain 추가
4. 배포 후 `curl https://buzz.ichapterwise.com/_liveness` 검증

## 기동 로컬 (참고, 이 머신선 불가)
```bash
# Docker + Rust + just 필요
just setup && just dev   # ws://localhost:3000
```

## 운영
- 매일: 데스크톱 앱 → `#inbox`(QAAgent 분류), `#content`(NewsAgent), `#data-ops`(DataAgent)
- 매주: `#releases` 에서 ReleaseAgent changelog → "ship it"
- 키 백업: `identity.md` Strict 규칙 (아동 PII 취급)

## 저작권
- Buzz: Apache 2.0 (block/buzz). 상업 사용 OK.
- 이 디렉토리 설정: 자유 수정.
