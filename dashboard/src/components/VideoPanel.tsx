'use client'
import { useState, useEffect } from 'react'

const VIDEO_TOPICS = [
  { label: '교육 뉴스 실시간', q: '대한민국 교육 뉴스 실시간' },
  { label: '입시 컨설팅', q: '2026 입시 컨설팅 설명회' },
  { label: 'EBS 수능 강의', q: 'EBSi 수능 강의' },
  { label: '교육정책 브리핑', q: '교육부 정책 브리핑 라이브' },
  { label: '유학 컨설팅', q: '해외 유학 컨설팅 세미나' },
]

interface VideoResult {
  video_id: string
  title: string
  channel: string
}

export default function VideoPanel() {
  const [open, setOpen] = useState(false)
  const [activeTopic, setActiveTopic] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [video, setVideo] = useState<VideoResult | null>(null)
  const [fetchedOnce, setFetchedOnce] = useState(false)

  const topic = VIDEO_TOPICS[activeTopic]
  const youtubeSearchUrl = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(topic.q)
  const fallbackEmbedUrl = 'https://www.youtube.com/embed?listType=search&list=' + encodeURIComponent(topic.q)

  useEffect(() => {
    if (!loaded) return
    setLoading(true)
    fetch(`/api/youtube?q=${encodeURIComponent(topic.q)}`)
      .then(r => r.json())
      .then(d => { setVideo(d.result); setFetchedOnce(true) })
      .catch(() => { setVideo(null); setFetchedOnce(true) })
      .finally(() => setLoading(false))
  }, [loaded, topic.q])

  const handleToggle = () => {
    setOpen(o => !o)
    setLoaded(true)
  }

  return (
    <>
      <button
        onClick={handleToggle}
        style={{
          position: 'absolute',
          bottom: 20,
          right: 270,
          background: open ? 'rgba(239,68,68,0.2)' : 'rgba(10,12,16,0.88)',
          border: '1px solid rgba(239,68,68,0.4)',
          borderRadius: 20,
          color: '#ef4444',
          padding: '6px 20px',
          fontSize: 11,
          fontWeight: 700,
          cursor: 'pointer',
          letterSpacing: '0.08em',
          backdropFilter: 'blur(12px)',
          zIndex: 10,
        }}
      >
        {open ? '▼ 영상 닫기' : '▶ 실시간 교육 영상'}
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          bottom: 70,
          right: 270,
          background: 'rgba(10,12,16,0.95)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 10,
          backdropFilter: 'blur(16px)',
          width: 380,
          overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
          zIndex: 9,
        }}>
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%', background: '#ef4444',
              display: 'inline-block', animation: 'video-live-pulse 1.2s infinite',
            }} />
            <span style={{ fontSize: 11.5, fontWeight: 700, color: '#f97316', letterSpacing: '0.04em' }}>
              실시간 교육 동영상
            </span>
          </div>

          <div style={{ padding: '12px 14px' }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' as const, marginBottom: 10 }}>
              {VIDEO_TOPICS.map((t, i) => (
                <button
                  key={t.label}
                  onClick={() => setActiveTopic(i)}
                  style={{
                    padding: '4px 10px', fontSize: 10, borderRadius: 12, cursor: 'pointer',
                    background: activeTopic === i ? '#ef4444' : 'rgba(255,255,255,0.06)',
                    color: activeTopic === i ? '#000' : '#94a3b8',
                    border: '1px solid rgba(255,255,255,0.1)',
                    fontWeight: activeTopic === i ? 700 : 400,
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {loading ? (
              <div style={{
                width: '100%', aspectRatio: '16 / 9', borderRadius: 8, background: '#000',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#94a3b8', fontSize: 11,
              }}>
                영상 검색 중...
              </div>
            ) : video ? (
              <>
                <iframe
                  src={`https://www.youtube.com/embed/${video.video_id}`}
                  allow="autoplay; encrypted-media"
                  allowFullScreen
                  style={{ width: '100%', aspectRatio: '16 / 9', border: 'none', borderRadius: 8, background: '#000' }}
                />
                <div style={{ fontSize: 10.5, color: '#94a3b8', marginTop: 8, lineHeight: 1.5 }}>
                  {video.title} · {video.channel}
                </div>
              </>
            ) : (
              <>
                <iframe
                  src={fallbackEmbedUrl}
                  title={`${topic.label} YouTube 검색 결과`}
                  allow="autoplay; encrypted-media"
                  allowFullScreen
                  style={{ width: '100%', aspectRatio: '16 / 9', border: 'none', borderRadius: 8, background: '#000' }}
                />
                <div style={{ fontSize: 10.5, color: '#94a3b8', marginTop: 8, lineHeight: 1.5 }}>
                  {fetchedOnce
                    ? 'API 키가 없어서 YouTube 검색 임베드로 대체 표시 중입니다.'
                    : 'YouTube 검색 임베드를 준비 중입니다.'}
                  {' '}
                  <a
                    href={youtubeSearchUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#ef4444', fontWeight: 700, textDecoration: 'none' }}
                  >
                    새 창에서 열기 ↗
                  </a>
                </div>
              </>
            )}
            <div style={{ fontSize: 10, color: '#64748b', marginTop: 8, lineHeight: 1.6 }}>
              YouTube Data API 키가 있으면 최신 영상 1건을 직접 임베드하고, 키가 없으면
              같은 검색어의 YouTube 검색 임베드로 대체합니다.
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes video-live-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </>
  )
}
