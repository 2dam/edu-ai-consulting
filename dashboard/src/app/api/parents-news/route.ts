import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

// 학부모On누리(www.parents.go.kr) 관련 뉴스 — /api/news와 같은 패턴이지만 백엔드의
// 별도 엔드포인트(/parents-news, 검색어만 '학부모' 계열로 다름)를 호출한다.
// 학부모On누리는 robots.txt가 크롤링을 막고 콘텐츠 API도 없어 사이트 자체 콘텐츠는
// 가져올 수 없다 — 네이버 뉴스 API로 관련 기사를 대신 보여준다(패널에서 출처를 명시).
function timeAgo(pubDate: string | null): string {
  if (!pubDate) return ''
  const diffMs = Date.now() - new Date(pubDate).getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  return `${Math.floor(hours / 24)}일 전`
}

type NewsItem = { title: string; source: string; url: string; category: string; pub_date: string | null }

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/parents-news?limit=15`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    })
    if (res.ok) {
      const data = await res.json()
      const items = (data.items || []).map((item: NewsItem) => ({
        title: item.title,
        source: item.source,
        time: timeAgo(item.pub_date),
        url: item.url,
      }))
      return NextResponse.json({ items, total: items.length, updated_at: new Date().toISOString() })
    }
    console.error('parents-news backend responded', res.status)
  } catch (err) {
    console.error('parents-news fetch failed', err)
  }
  return NextResponse.json({ items: [], total: 0, updated_at: new Date().toISOString() })
}
