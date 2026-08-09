# DNS / Custom Domain 설정 — buzz.ichapterwise.com

⚠️ **이 문서는 설정 지침입니다. 실제 DNS 레코드 생성은 본인이 도메인
레지스트라/클라우드 DNS 콘솔에서 수행** (에이전트는 해당 콘솔 접근 권한 없음).

## 1) Render 에서 Custom Domain 추가
1. Render 대시보드 → `edu-ai-consulting-buzz` 서비스 → **Settings → Custom Domains**
2. `buzz.ichapterwise.com` 입력 → Render 가 **CNAME/DNS 검증용 값** 2개를 줌:
   - **Verification TXT** (예: `_buzz.ichapterwise.com` TXT `render-verify=...`)
   - **CNAME** (예: `buzz.ichapterwise.com` → `srv-xxxx.onrender.com`)
3. 아래 값을 도메인 DNS 에 등록.

## 2) 도메인 DNS 레코드 (예: 가비아/후이즈/Cloudflare/Route53)

| 유형 | 호스트/이름 | 값/대상 | 비고 |
|------|------------|---------|------|
| CNAME | `buzz` | `srv-xxxx.onrender.com` (Render 제공값) | 실제 렌더 호스트로 교체 |
| TXT | `_buzz` (또는 `_buzz.ichapterwise.com`) | `render-verify=xxxxxxxx` | Render 검증용(추후 삭제 가능) |

> Cloudflare 사용 시: CNAME 의 **Proxy 상태를 잠시 grey-cloud(DNS only)** 로 두고
> Render 인증서 발급 후 orange-cloud(Proxy) 켜도 됨. WebSocket(wss://) 은 Proxy 에서
> 기본 지원하나, 문제 시 DNS-only 로 테스트.

## 3) Render 자동 TLS
- Custom Domain 추가 시 Render 가 Let's Encrypt 인증서를 자동 발급/갱신.
- `RELAY_URL=wss://buzz.ichapterwise.com` 이 인증서로 보호됨.

## 4) 클라이언트 연결
- Buzz 데스크톱 앱: `BUZZ_RELAY_URL=wss://buzz.ichapterwise.com`
- 또는 앱 내 릴레이 전환 메뉴에서 위 URL 입력.

## 5) 검증 (배포 후)
```bash
curl -fsS https://buzz.ichapterwise.com/_liveness   # 200 이면 정상
dig +short buzz.ichapterwise.com                    # Render IP/CNAME 확인
```

## 6) ichapterwise.com 자체는?
- 기존 Render 서비스(api/dashboard/community)가 `ichapterwise.com` / `app.ichapterwise.com`
  로 이미 바인딩되어 있음. `buzz.` 서브도메인은 **추가 서비스** 이므로 충돌 없음.
- 메인 도메인이 Cloudflare/Render 로 이미 관리 중이면, 같은 존에 `buzz` CNAME 만 추가.

## 7) 주의
- Render 무료/Starter 인스턴스는 가용성/메모리 제약 있음. Buzz 릴레이는
  Postgres+Redis+MinIO 를 요구 → Render Postgres/Redis 애드온 연결 또는
  외부 MinIO 필요. 인스턴스 메모리 부족 시 `standard` 플랜으로 상향.
- secret(RELAY_OWNER_PUBKEY 등)은 Render Environment 에서 직접 입력, 절대 커밋 금지.
