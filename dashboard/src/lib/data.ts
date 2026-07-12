/**
 * 한국 교육 인텔리전스 데이터 레이어 정의.
 * 실제 수집 데이터(FastAPI /records)와 공공 데이터 소스를 혼합한다.
 */

export const KOREA_CENTER = { lng: 127.8, lat: 36.5, zoom: 6.5 }
export const GANGNAM_CENTER = { lng: 127.05, lat: 37.51, zoom: 13 }

export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  (process.env.NODE_ENV === 'production' ? 'https://ichapterwise.com' : 'http://localhost:8000')

// ── 전국 주요 교육 거점 (공공 데이터 기반 기본값) ──────────────────────────

export interface AcademyNode {
  id: string
  name: string
  region: string
  lat: number
  lng: number
  academy_count: number       // 해당 구·시 학원 수 — /region-stats(실제 크롤링 집계)로 런타임에 덮어써짐
  gap_index: number           // 교육격차지수 (0~1, 높을수록 격차 큼) — 마찬가지로 런타임에 실제값으로 대체
  tier: 'S' | 'A' | 'B' | 'C'
}

// 전국 주요 지역의 이름·좌표(실제) 시드 목록. academy_count/gap_index/tier는 여기 적힌 값이
// 그대로 쓰이지 않고, dashboard/src/app/api/education/route.ts가 백엔드 /region-stats(실제
// 크롤링 데이터 집계)를 불러와 덮어쓴다 — 초기 렌더/백엔드 미연결 시의 폴백 값일 뿐이다.
export const REGION_NODES: AcademyNode[] = [
  { id: 'gangnam', name: '강남구', region: '서울', lat: 37.5172, lng: 127.0473, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'seocho',  name: '서초구', region: '서울', lat: 37.4837, lng: 127.0324, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'songpa',  name: '송파구', region: '서울', lat: 37.5145, lng: 127.1059, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'mapo',    name: '마포구', region: '서울', lat: 37.5638, lng: 126.9084, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'nowon',   name: '노원구', region: '서울', lat: 37.6543, lng: 127.0568, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'busan',   name: '부산시', region: '부산', lat: 35.1796, lng: 129.0756, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'daegu',   name: '대구시', region: '대구', lat: 35.8714, lng: 128.6014, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'incheon', name: '인천시', region: '인천', lat: 37.4563, lng: 126.7052, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'gwangju', name: '광주시', region: '광주', lat: 35.1595, lng: 126.8526, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'daejeon', name: '대전시', region: '대전', lat: 36.3504, lng: 127.3845, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'ulsan',   name: '울산시', region: '울산', lat: 35.5384, lng: 129.3114, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'sejong',  name: '세종시', region: '세종', lat: 36.4800, lng: 127.2890, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'suwon',   name: '수원시', region: '경기', lat: 37.2636, lng: 127.0286, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'changwon',name: '창원시', region: '경남', lat: 35.2280, lng: 128.6811, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'cheongju',name: '청주시', region: '충북', lat: 36.6424, lng: 127.4890, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'jeonju',  name: '전주시', region: '전북', lat: 35.8242, lng: 127.1480, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'chuncheon',name:'춘천시', region: '강원', lat: 37.8813, lng: 127.7298, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'jeju',    name: '제주시', region: '제주', lat: 33.4996, lng: 126.5312, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'mokpo',   name: '목포시', region: '전남', lat: 34.8118, lng: 126.3922, academy_count: 0, gap_index: 0, tier: 'C' },
  { id: 'pohang',  name: '포항시', region: '경북', lat: 36.0190, lng: 129.3435, academy_count: 0, gap_index: 0, tier: 'C' },
]

// ── 레이어 정의 ───────────────────────────────────────────────────────────────
// "강남 8학군" 레이어(하드코딩된 학원 8곳, 위도/경도 지어냄)는 제거했다 — 실제 학원
// 데이터(나이스 학원교습소정보)는 좌표가 없어 지도 핀으로 못 그리므로, "시설 평가정보"
// 탭에서 facility_type=학원 + 지역 검색("강남구")으로 목록을 보는 쪽으로 대체한다.

export const LAYERS = [
  { id: 'academy-density',  label: '학원 밀도',        icon: '🏫', color: '#f97316', default: true },
  { id: 'gap-heatmap',      label: '교육격차 히트맵',   icon: '🌡️', color: '#ef4444', default: true },
  { id: 'dropout-risk',     label: '중도탈락 위험도 (시범)', icon: '⚠️', color: '#a855f7', default: false },
  { id: 'universities',     label: '주요 대학',         icon: '🎓', color: '#3b82f6', default: false },
  { id: 'early-education',  label: '어린이집·유치원·초등·학원',icon: '🧸', color: '#ec4899', default: false },
  { id: 'cctv',             label: '전국 공공 CCTV',    icon: '📹', color: '#14b8a6', default: false },
  { id: 'loop-status',      label: 'AI 루프 상태',      icon: '🤖', color: '#22c55e', default: true },
] as const

export type LayerId = typeof LAYERS[number]['id']

// ── 전국 공공 CCTV (국가교통정보센터 ITS, 도로 구간만) ────────────────────────

export interface CctvPoint {
  name: string
  lat: number
  lng: number
  stream_url: string
  format: string
}

// ── 어린이집·유치원·초등학교·학원 기초자료 + 공식 평가/등록 정보 ──────────────
// "리뷰"는 네이버/카카오 등 민간 리뷰가 아니라 공식 출처(평가인증·정보공시·등록현황)만 다룬다.

export type FacilityType = 'daycare' | 'kindergarten' | 'elementary' | 'academy' | 'university'

export const FACILITY_TYPE_LABEL: Record<FacilityType, string> = {
  daycare: '어린이집',
  kindergarten: '유치원',
  elementary: '초등학교',
  academy: '학원',
  university: '대학',
}

export interface EducationFacility {
  id: number
  data: {
    facility_type: FacilityType
    name: string
    region: string
    address: string
    establishment_type?: string
    capacity?: number | null
    current_enrollment?: number | null
    evaluation_grade?: string   // 어린이집평가제 등급 등 공식 평가 결과
    status_note?: string        // 등록상태·행정처분 이력 요약 (학원 등)
    // 원본 공공데이터는 대부분 주소만 제공 — 지도 표시를 위해서는 별도 지오코딩이 필요하다.
    // (다음 단계: 주소 -> 좌표 변환 배치 작업을 pipelines.py 에 추가)
    lat?: number
    lng?: number
    is_sample?: boolean   // true면 크롤러가 아직 안 돌아 화면 구성 확인용으로 넣은 예시 데이터
  }
  created_at: string
}

// crawler/early_education_spider 를 아직 실행하지 않았거나 API 키가 없을 때도
// 화면(지도 점·평가정보 패널)이 비어 보이지 않도록 하는 예시 데이터.
// 실제 시설이 아니라 화면 구성 확인용 placeholder이며, 실제 수집 데이터가 들어오면
// (page.tsx) 자동으로 대체된다.
export const SAMPLE_EDUCATION_FACILITIES: EducationFacility[] = [
  { id: -1, created_at: '', data: { facility_type: 'daycare', name: '대치동 A어린이집 (예시)', region: '서울 강남구', address: '서울 강남구 대치동 (예시 주소)', evaluation_grade: '최우수 (예시)', lat: 37.4975, lng: 127.0620, is_sample: true } },
  { id: -2, created_at: '', data: { facility_type: 'daycare', name: '역삼동 B어린이집 (예시)', region: '서울 강남구', address: '서울 강남구 역삼동 (예시 주소)', evaluation_grade: '우수 (예시)', lat: 37.5006, lng: 127.0365, is_sample: true } },
  { id: -3, created_at: '', data: { facility_type: 'kindergarten', name: '서초 C유치원 (예시)', region: '서울 서초구', address: '서울 서초구 서초동 (예시 주소)', establishment_type: '사립 (예시)', lat: 37.4920, lng: 127.0165, is_sample: true } },
  { id: -4, created_at: '', data: { facility_type: 'kindergarten', name: '반포 D유치원 (예시)', region: '서울 서초구', address: '서울 서초구 반포동 (예시 주소)', establishment_type: '국공립 (예시)', lat: 37.5045, lng: 127.0090, is_sample: true } },
  { id: -5, created_at: '', data: { facility_type: 'elementary', name: '대치초등학교 (예시)', region: '서울', address: '서울 강남구 대치동 (예시 주소)', establishment_type: '공립 (예시)', lat: 37.4950, lng: 127.0580, is_sample: true } },
  { id: -6, created_at: '', data: { facility_type: 'elementary', name: '역삼초등학교 (예시)', region: '서울', address: '서울 강남구 역삼동 (예시 주소)', establishment_type: '공립 (예시)', lat: 37.5000, lng: 127.0400, is_sample: true } },
  { id: -7, created_at: '', data: { facility_type: 'academy', name: '대치 E학원 (예시)', region: '서울 강남구', address: '서울 강남구 대치동 (예시 주소)', establishment_type: '수학·과학 (예시)', status_note: '등록 정상 (예시)', lat: 37.4965, lng: 127.0630, is_sample: true } },
  { id: -8, created_at: '', data: { facility_type: 'academy', name: '압구정 F학원 (예시)', region: '서울 강남구', address: '서울 강남구 압구정동 (예시 주소)', establishment_type: '영어 (예시)', status_note: '등록 정상 (예시)', lat: 37.5272, lng: 127.0286, is_sample: true } },
]

// ── 공공 API 소스 ─────────────────────────────────────────────────────────────

export const DATA_SOURCES = [
  { name: '교육통계서비스',  url: 'https://kess.kedi.re.kr', status: 'active' },
  { name: '나이스(NICE)',    url: 'https://www.neis.go.kr',  status: 'active' },
  { name: '수능통계',        url: 'https://www.suneung.re.kr', status: 'active' },
  { name: '학원정보',        url: 'https://www.hag-won.info', status: 'active' },
  { name: 'FastAPI 백엔드',  url: BACKEND_URL,               status: 'active' },
]
