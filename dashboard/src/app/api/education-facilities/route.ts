import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

const FACILITY_TYPES = ['daycare', 'kindergarten', 'elementary', 'academy', 'university']
const PER_TYPE_LIMIT = 600 // 5개 타입 * 600 = 3000, 기존 서버 상한과 동일한 총량 유지

// 어린이집·유치원·초등학교·학원·대학 기초자료 (crawler/early_education_spider 수집분).
//
// facility_type 없이 최근 N건만 가져오면, 특정 타입의 크롤이 대량으로 몰린 날(예: 유치원
// 8만여건 적재)엔 그 타입이 최근 N건을 통째로 차지해서 다른 타입이 하나도 안 보이게 된다.
// 타입별로 나눠 병렬 조회한 뒤 합쳐서, 어떤 타입 하나가 몰려 들어와도 나머지가 묻히지 않게 한다.
export async function GET() {
  try {
    const responses = await Promise.all(
      FACILITY_TYPES.map(t =>
        fetch(`${BACKEND_URL}/education-facilities?facility_type=${t}&limit=${PER_TYPE_LIMIT}`, {
          cache: 'no-store',
          signal: AbortSignal.timeout(30000),
        }).then(r => (r.ok ? r.json() : { items: [], summary_by_type: {} }))
      )
    )
    const items = responses.flatMap(r => r.items || [])
    const summary_by_type: Record<string, number> = {}
    for (const r of responses) {
      for (const [k, v] of Object.entries(r.summary_by_type || {})) {
        summary_by_type[k] = (summary_by_type[k] || 0) + (v as number)
      }
    }
    return NextResponse.json({ items, total: items.length, summary_by_type })
  } catch (err) {
    // 백엔드 미실행/타임아웃 시 빈 목록으로 폴백 — 원인은 로그에 남긴다.
    console.error('education-facilities fetch failed', err)
  }
  return NextResponse.json({ items: [], total: 0, summary_by_type: {} })
}
