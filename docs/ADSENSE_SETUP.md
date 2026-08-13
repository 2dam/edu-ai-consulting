# EduIntel (edu-ai-consulting) — Google AdSense 적용 가이드

> 도메인: **doke-v.net** (메인 대시보드) / **community.doke-v.net** (커뮤니티)
> 프론트엔드: `dashboard` (Next.js 15) + `dashboard-community` (Vite/React)

이 저장소에는 AdSense 광고를 **코드 레벨**에서 받을 수 있는 구조가 이미 마련되어 있습니다.
아래는 "코드가 들어간 상태"에서 실제 수익이 나기까지의 단계별 절차입니다.

---

## 1. AdSense 계정 생성

1. https://www.google.com/adsense/ 접속 → **가입**
2. 로그인 Google 계정 선택 (개인/사업자)
3. **사이트 추가** 단계에서 운영 도메인 입력:
   - `doke-v.net`
   - `community.doke-v.net`
4. 결제/수령 정보(은행계좌, 주소) 입력 — 수익 지급용

---

## 2. 게시자 ID 확인 및 환경변수 채우기

AdSense 좌측 메뉴 **내 계정 → 게시자 ID** 형식: `pub-XXXXXXXXXXXXXXXX` (16자리)

받은 값을 각 앱의 `.env`(절대 커밋 금지)에 입력:

### dashboard (Next.js)
`dashboard/.env.local`
```
NEXT_PUBLIC_ADSENSE_PUBLISHER_ID=pub-실제ID
NEXT_PUBLIC_SITE_DOMAIN=doke-v.net
NEXT_PUBLIC_ADS_ENABLED=true
```

### dashboard-community (Vite)
`dashboard-community/.env.production` (Render 빌드용)
```
VITE_ADSENSE_PUBLISHER_ID=pub-실제ID
VITE_SITE_DOMAIN=doke-v.net
VITE_ADS_ENABLED=true
# 광고단위 슬롯 ID (AdSense → 광고 → 광고단위에서 복사, 선택)
VITE_AD_SLOT_TOP=
VITE_AD_SLOT_FEED=
VITE_AD_SLOT_SIDEBAR=
```
> 플레이스홀더(`pub-0...`) 상태에서는 스크립트가 로드되지 않아 광고가 **뜨지 않습니다** (승인 전 안전 기본값).

---

## 3. 사이트 연결 확인 (메타태그 / ads.txt)

AdSense가 사이트 소유를 확인합니다. 이 저장소는 두 가지를 모두 지원합니다.

- **자동 연결**: 일부 경우 AdSense가 자동으로 확인. 안 되면 아래 중 택1.
- **ads.txt**: 이 저장소는 빌드 시 자동 생성됩니다.
  - `dashboard` → `/ads.txt` 라우트 (게시자 ID 환경변수에서 읽음)
  - `dashboard-community` → `public/ads.txt` 가 빌드 시 치환됨
  - **검증**: 배포 후 `https://doke-v.net/ads.txt` 와 `https://community.doke-v.net/ads.txt` 가
    `google.com, pub-실제ID, DIRECT, f08c47fec0942fa0` 형태로 떠야 함.

---

## 4. 사이트 검토 / 승인 요청

AdSense → **사이트** → 상태가 "준비됨"이 되면 **검토 요청**.
- 승인까지 보통 며칠~2주 (콘텐츠 품질·정책 준수 여부에 따라 상이)
- 승인 전에는 광고가 표시되지 않음

---

## 5. 광고 배치 (이미 코드에 들어가 있음)

| 위치 | 컴포넌트 | 파일 |
|------|----------|------|
| 메인 콘텐츠 상단 | `AdBanner` (사이드바 슬롯) | `dashboard-community/src/components/layout/AppShell.tsx` |
| 뉴스 피드 중간 (3번째 카드 뒤) | `AdBanner` (피드 슬롯) | `dashboard-community/src/pages/NewsFeed.tsx` |
| 쿠키/개인정보 동의 배너 | `AdConsentBanner` | 양쪽 `src/components/AdConsentBanner.tsx` |
| 동의 상태 관리/스크립트 로더 | `AdsConsentProvider` | 양쪽 `src/lib/adsense.ts` |

**권장 순서**
1. 초기: **자동 광고** (AdSense가 위치 자동 결정) → 데이터 확보
2. 이후: 직접 광고단위(`VITE_AD_SLOT_*`)로 위치 최적화

**UX 원칙 (이미 적용)**
- 방문자 동의 전엔 광고 스크립트 로드 안 함 (개인정보보호법/GDPR)
- 화면 도배 금지 — 콘텐츠 사이에만 배치
- AI 분석 결과 **바로 위/아래**에 광고를 섞지 않음 (추천 오인 방지)

---

## 6. 도메인 DNS 설정 (호스팅거 → Render)

`doke-v.net`은 현재 호스팅거에서 응답 중(IP `2.57.91.91`). Render로 옮기려면:

1. Render 대시보드에서 `edu-ai-consulting-dashboard` / `edu-ai-consulting-community` 서비스의
   **Settings → Custom Domains** 에 `doke-v.net`, `www.doke-v.net`, `community.doke-v.net` 추가
2. Render가 안내하는 **CNAME/A 레코드** 값 확인
3. 호스팅거 DNS 관리에서 기존 `doke-v.net` 레코드를 Render 값으로 변경
4. 전파 완료 후(수분~수시간) Render에서 TLS 인증서 자동 발급

> 참고: 백엔드 API는 `ichapterwise.com`(Render) 그대로 둡니다. 프론트엔드만 `doke-v.net`으로.

---

## 7. 검증 체크리스트

- [ ] `https://doke-v.net/ads.txt` → `google.com, pub-..., DIRECT, ...` 출력
- [ ] `https://community.doke-v.net/ads.txt` 동일
- [ ] 첫 방문 시 하단에 동의 배너 노출
- [ ] '동의' 클릭 후 `pagead2.googlesyndication.com` 스크립트 로드 (DevTools Network 탭)
- [ ] AdSense 승인 후 광고 표시 (최대 1시간 지연 가능)
- [ ] 모바일에서 반응형 광고 정상 노출

---

## 8. 수익 모니터링

AdSense → **보고서**: RPM / CTR / 페이지뷰 확인.
회원 10만+ 단계부터 직접 교육기관 광고 영업(AdSense + 직접 광고)으로 확장 권장.
