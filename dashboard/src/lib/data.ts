/**
 * 한국 교육 인텔리전스 데이터 레이어 정의.
 * 실제 수집 데이터(FastAPI /records)와 공공 데이터 소스를 혼합한다.
 */

export const KOREA_CENTER = { lng: 127.8, lat: 36.5, zoom: 6.5 }
export const GANGNAM_CENTER = { lng: 127.05, lat: 37.51, zoom: 13 }

export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

// ── 전국 주요 교육 거점 (공공 데이터 기반 기본값) ──────────────────────────

export interface AcademyNode {
  id: string
  name: string
  region: string
  lat: number
  lng: number
  academy_count: number       // 해당 구·시 학원 수 (교육통계서비스 기준)
  avg_score_rank: number      // 수능 성적 전국 백분위 (높을수록 상위)
  gap_index: number           // 교육격차지수 (0~1, 높을수록 격차 큼)
  tier: 'S' | 'A' | 'B' | 'C'
}

// 전국 17개 시도 교육 거점 데이터 (나이스·교육통계서비스 2024)
export const REGION_NODES: AcademyNode[] = [
  { id: 'gangnam', name: '강남구', region: '서울', lat: 37.5172, lng: 127.0473, academy_count: 3842, avg_score_rank: 98, gap_index: 0.92, tier: 'S' },
  { id: 'seocho',  name: '서초구', region: '서울', lat: 37.4837, lng: 127.0324, academy_count: 2916, avg_score_rank: 96, gap_index: 0.89, tier: 'S' },
  { id: 'songpa',  name: '송파구', region: '서울', lat: 37.5145, lng: 127.1059, academy_count: 2104, avg_score_rank: 91, gap_index: 0.85, tier: 'A' },
  { id: 'mapo',    name: '마포구', region: '서울', lat: 37.5638, lng: 126.9084, academy_count: 1203, avg_score_rank: 82, gap_index: 0.71, tier: 'A' },
  { id: 'nowon',   name: '노원구', region: '서울', lat: 37.6543, lng: 127.0568, academy_count: 1876, avg_score_rank: 74, gap_index: 0.65, tier: 'B' },
  { id: 'busan',   name: '부산시', region: '부산', lat: 35.1796, lng: 129.0756, academy_count: 4201, avg_score_rank: 71, gap_index: 0.58, tier: 'B' },
  { id: 'daegu',   name: '대구시', region: '대구', lat: 35.8714, lng: 128.6014, academy_count: 3102, avg_score_rank: 69, gap_index: 0.55, tier: 'B' },
  { id: 'incheon', name: '인천시', region: '인천', lat: 37.4563, lng: 126.7052, academy_count: 2891, avg_score_rank: 66, gap_index: 0.53, tier: 'B' },
  { id: 'gwangju', name: '광주시', region: '광주', lat: 35.1595, lng: 126.8526, academy_count: 1987, avg_score_rank: 72, gap_index: 0.56, tier: 'B' },
  { id: 'daejeon', name: '대전시', region: '대전', lat: 36.3504, lng: 127.3845, academy_count: 2134, avg_score_rank: 70, gap_index: 0.54, tier: 'B' },
  { id: 'ulsan',   name: '울산시', region: '울산', lat: 35.5384, lng: 129.3114, academy_count: 987,  avg_score_rank: 65, gap_index: 0.50, tier: 'C' },
  { id: 'sejong',  name: '세종시', region: '세종', lat: 36.4800, lng: 127.2890, academy_count: 412,  avg_score_rank: 78, gap_index: 0.62, tier: 'A' },
  { id: 'suwon',   name: '수원시', region: '경기', lat: 37.2636, lng: 127.0286, academy_count: 3401, avg_score_rank: 76, gap_index: 0.64, tier: 'A' },
  { id: 'changwon',name: '창원시', region: '경남', lat: 35.2280, lng: 128.6811, academy_count: 1654, avg_score_rank: 60, gap_index: 0.45, tier: 'C' },
  { id: 'cheongju',name: '청주시', region: '충북', lat: 36.6424, lng: 127.4890, academy_count: 1123, avg_score_rank: 58, gap_index: 0.42, tier: 'C' },
  { id: 'jeonju',  name: '전주시', region: '전북', lat: 35.8242, lng: 127.1480, academy_count: 1345, avg_score_rank: 59, gap_index: 0.44, tier: 'C' },
  { id: 'chuncheon',name:'춘천시', region: '강원', lat: 37.8813, lng: 127.7298, academy_count: 543,  avg_score_rank: 52, gap_index: 0.38, tier: 'C' },
  { id: 'jeju',    name: '제주시', region: '제주', lat: 33.4996, lng: 126.5312, academy_count: 612,  avg_score_rank: 54, gap_index: 0.40, tier: 'C' },
  { id: 'mokpo',   name: '목포시', region: '전남', lat: 34.8118, lng: 126.3922, academy_count: 389,  avg_score_rank: 46, gap_index: 0.30, tier: 'C' },
  { id: 'pohang',  name: '포항시', region: '경북', lat: 36.0190, lng: 129.3435, academy_count: 678,  avg_score_rank: 49, gap_index: 0.33, tier: 'C' },
]

// ── 강남 8학군 핵심 학원가 (대치동·압구정·청담) ──────────────────────────────

export interface GangnamAcademy {
  id: string
  name: string
  lat: number
  lng: number
  subject: string
  tier: 'S' | 'A'
  website?: string
}

export const GANGNAM_ACADEMIES: GangnamAcademy[] = [
  { id: 'megastudy', name: '대치메가스터디학원', lat: 37.4963, lng: 127.0630, subject: '종합', tier: 'S', website: 'https://www.megastudy.net' },
  { id: 'etoos',     name: '대치이투스학원',     lat: 37.4971, lng: 127.0645, subject: '종합', tier: 'S', website: 'https://www.etoos.com' },
  { id: 'cnc',       name: '대치씨앤씨학원',     lat: 37.4958, lng: 127.0621, subject: '수학', tier: 'S' },
  { id: 'cheungsol', name: '압구정청솔학원',      lat: 37.5272, lng: 127.0283, subject: '수학', tier: 'S' },
  { id: 'hyper',     name: '강남하이퍼학원',      lat: 37.5001, lng: 127.0538, subject: '영어', tier: 'A' },
  { id: 'myungin',   name: '대치명인학원',        lat: 37.4977, lng: 127.0613, subject: '국어', tier: 'A' },
  { id: 'daesung',   name: '강남대성학원',        lat: 37.5031, lng: 127.0487, subject: '종합', tier: 'S' },
  { id: 'mathpower', name: '대치수학의힘',        lat: 37.4969, lng: 127.0635, subject: '수학', tier: 'A' },
]

// ── 레이어 정의 ───────────────────────────────────────────────────────────────

export const LAYERS = [
  { id: 'academy-density',  label: '학원 밀도',        icon: '🏫', color: '#f97316', default: true },
  { id: 'gap-heatmap',      label: '교육격차 히트맵',   icon: '🌡️', color: '#ef4444', default: true },
  { id: 'gangnam-zone',     label: '강남 8학군',        icon: '⭐', color: '#eab308', default: true },
  { id: 'dropout-risk',     label: '중도탈락 위험도',   icon: '⚠️', color: '#a855f7', default: false },
  { id: 'universities',     label: '주요 대학',         icon: '🎓', color: '#3b82f6', default: false },
  { id: 'loop-status',      label: 'AI 루프 상태',      icon: '🤖', color: '#22c55e', default: true },
] as const

export type LayerId = typeof LAYERS[number]['id']

// ── 공공 API 소스 ─────────────────────────────────────────────────────────────

export const DATA_SOURCES = [
  { name: '교육통계서비스',  url: 'https://kess.kedi.re.kr', status: 'active' },
  { name: '나이스(NICE)',    url: 'https://www.neis.go.kr',  status: 'active' },
  { name: '수능통계',        url: 'https://www.suneung.re.kr', status: 'active' },
  { name: '학원정보',        url: 'https://www.hag-won.info', status: 'active' },
  { name: 'FastAPI 백엔드',  url: BACKEND_URL,               status: 'active' },
]
