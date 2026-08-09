# 아이덴티티 관리 — npub / nsec (EduIntel 운영자 + AI 직원)

Buzz는 암호화 키가 곧 정체. **교육 플랫폼은 아동·학생 PII 를 다루므로 키 관리가
보안·컴플라이언스의 일부.** 분실=정체 상실=복구 불가.

## 키 종류
- **npub** (공개키, 64자 헥스/bech32) — RELAY_OWNER_PUBKEY, 에이전트 공개키
- **nsec** (비밀키) — 절대 유출 금지, BUZZ_PRIVATE_KEY 로 기동

## 발급
1. 데스크톱 앱 최초 실행 시 자동 생성(오너)
2. 에이전트 6개 키는 각각 별도 생성 → Render secret `BUZZ_RELAY_PRIVATE_KEY`(오너)
   및 각 에이전트 기동 시 주입(필요 시 별도 secret)

## 백업 규칙 (Strict — 교육 데이터 취급)
- [ ] 오너 nsec → 오프라인 2곳 (보안 USB + 패스워드 매니저 암호화 vault)
- [ ] 에이전트 nsec 6개 → 별도 vault, 역할 라벨링
- [ ] Render secret 스냅샷 → 암호화 오프라인
- [ ] 하드웨어 보안키(패스키) 권장

## 분실 시나리오
| 분실 | 결과 | 대처 |
|------|------|------|
| 오너 nsec | 정체/오너권한 상실 | 새 키, RELAY_OWNER_PUBKEY 교체, 이력 단절 |
| 에이전트 nsec | 해당 직원 정체 상실 | npub 제거 후 재발급, 이력 초기화 |
| Render secret 유출 | DB/미디어 노출 위험 | 즉시 교체+재기동, S3 키 로테이션 |

## 보안 수칙 (교육 맥락 추가)
- nsec 절대 채팅/커밋/로그 출력 금지 (CI 마스킹)
- 닫힌 릴레이(`BUZZ_REQUIRE_RELAY_MEMBERSHIP=true`) 유지
- 주기적 멤버 점검 — 모르는 npub 없나
- **PII 원칙**: 수집 단계 AnonymizePipeline 이 학생 실명/연락처 제거.
  Buzz 채널에도 실명/연락처/아동 정보 금지. 위반 시 즉시 삭제+운영자 통보.
