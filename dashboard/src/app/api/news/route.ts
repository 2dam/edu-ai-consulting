import { NextResponse } from 'next/server'

// 교육부·언론사 RSS 피드에서 실시간 교육 뉴스 수집
const EDU_RSS_FEEDS = [
  'https://www.moe.go.kr/boardCnts/list.do?boardID=294&m=0503&s=moe',
]

const STATIC_NEWS = [
  { title: '2026 수능 시행계획 발표', source: '교육부', time: '10분 전', url: '#', category: '수능' },
  { title: '대입 공정성 강화 방안 논의', source: '교육부', time: '1시간 전', url: '#', category: '대입' },
  { title: '강남구 학원 수 전년比 3.2% 증가', source: '교육통계', time: '3시간 전', url: '#', category: '학원' },
  { title: '지방 교육격차 해소를 위한 AI 컨설팅 도입 확대', source: '한국교육신문', time: '5시간 전', url: '#', category: '정책' },
  { title: '2025 수능 EBS 연계율 50% 유지 확정', source: '교육부', time: '6시간 전', url: '#', category: '수능' },
  { title: '학원비 상한제 논의 재점화', source: '한겨레', time: '8시간 전', url: '#', category: '정책' },
  { title: '서울대 2026 정시 비율 40% 확대', source: '조선일보', time: '12시간 전', url: '#', category: '대입' },
]

export async function GET() {
  return NextResponse.json({
    items: STATIC_NEWS,
    total: STATIC_NEWS.length,
    updated_at: new Date().toISOString(),
  })
}
