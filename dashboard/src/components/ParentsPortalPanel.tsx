'use client'
import { useEffect, useState } from 'react'

// 학부모On누리(www.parents.go.kr) — 교육부·국가평생교육진흥원 전국학부모지원센터가
// 운영하는 공식 학부모 교육정보 포털. robots.txt가 크롤링을 막고 콘텐츠 API도 없어
// 사이트 자체 게시물은 가져올 수 없다(이 프로젝트는 ROBOTSTXT_OBEY=True를 항상 지킨다).
// 대신 이미 연동된 네이버 뉴스 API로 '학부모' 관련 기사를 모아 비슷한 실시간 피드를
// 보여주고, 실제 포털로 가는 공식 링크를 함께 둔다 — 자체 게시물이 아님을 명시한다.
const PARENTS_PORTAL_URL = 'https://www.parents.go.kr/'

type NewsItem = { title: string; source: string; time: string; url: string }

export default function ParentsPortalPanel() {
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/parents-news')
      .then(r => r.json())
      .then(d => setItems(d.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{
      position: 'absolute',
      right: 16,
      top: 252,
      width: 240,
      maxHeight: 'calc(100vh - 512px)',
      overflowY: 'auto',
      background: 'rgba(10,12,16,0.9)',
      border: '1px solid rgba(59,130,246,0.28)',
      borderRadius: 8,
      backdropFilter: 'blur(12px)',
      padding: '13px 14px',
      color: '#e2e8f0',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%', background: '#3b82f6', flexShrink: 0,
        }} />
        <span style={{ fontSize: 10, color: '#60a5fa', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          학부모On누리
        </span>
      </div>
      <div style={{ fontSize: 9.5, color: '#64748b', lineHeight: 1.5, marginBottom: 10 }}>
        학부모On누리 자체 게시물이 아닌, 관련 교육 전문매체 뉴스입니다(네이버 뉴스 API).
      </div>

      {loading ? (
        <div style={{ fontSize: 11, color: '#64748b' }}>불러오는 중...</div>
      ) : items.length === 0 ? (
        <div style={{ fontSize: 11, color: '#64748b', lineHeight: 1.6 }}>표시할 기사가 없습니다.</div>
      ) : (
        items.map((item, i) => (
          <a
            key={i}
            href={item.url}
            target="_blank"
            rel="noreferrer"
            style={{ display: 'block', textDecoration: 'none', color: 'inherit', marginBottom: 10 }}
          >
            <div style={{ fontSize: 11, lineHeight: 1.4, color: '#e2e8f0', marginBottom: 2 }}>
              {item.title}
            </div>
            <div style={{ fontSize: 9.5, color: '#64748b' }}>
              {item.source} · {item.time}
            </div>
          </a>
        ))
      )}

      <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '10px 0' }} />
      <a
        href={PARENTS_PORTAL_URL}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'block',
          textAlign: 'center' as const,
          color: '#0a0c10',
          background: '#3b82f6',
          borderRadius: 6,
          padding: '6px 10px',
          fontSize: 10.5,
          fontWeight: 800,
          textDecoration: 'none',
        }}
      >
        학부모On누리 공식 사이트 ↗
      </a>
    </div>
  )
}
