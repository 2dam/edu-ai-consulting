import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

// 실시간 교육 뉴스 — 네이버 뉴스 검색 오픈API (FastAPI 백엔드 경유).
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
    const res = await fetch(`${BACKEND_URL}/education-news?limit=20`, {
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
        category: item.category,
      }))
      return NextResponse.json({ items, total: items.length, updated_at: new Date().toISOString() })
    }
    console.error('education-news backend responded', res.status)
  } catch (err) {
    console.error('education-news fetch failed', err)
  }
  return NextResponse.json({ items: [], total: 0, updated_at: new Date().toISOString() })
}
