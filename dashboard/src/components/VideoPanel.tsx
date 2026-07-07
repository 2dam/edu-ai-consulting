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
          right: 310,
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
          right: 310,
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

            {video ? (
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
              <div style={{
                width: '100%', aspectRatio: '16 / 9', borderRadius: 8, background: '#000',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 10,
                padding: 16, boxSizing: 'border-box' as const,
              }}>
                <div style={{ fontSize: 11, color: '#64748b', textAlign: 'center' as const, lineHeight: 1.6 }}>
                  {loading
                    ? '영상 검색 중...'
                    : fetchedOnce
                      ? 'YOUTUBE_API_KEY가 아직 설정되지 않았거나 검색 결과가 없습니다.'
                      : ''}
                </div>
                <a
                  href={`https://www.youtube.com/results?search_query=${encodeURIComponent(topic.q)}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: 11, color: '#ef4444', fontWeight: 700, textDecoration: 'none' }}
                >
                  YouTube에서 직접 검색하기 ↗
                </a>
              </div>
            )}

            <div style={{ fontSize: 10, color: '#64748b', marginTop: 8, lineHeight: 1.6 }}>
              YouTube Data API로 검색어에 맞는 최신 영상 1건을 임베드합니다. 주제를 바꾸면
              해당 주제의 최신 영상으로 갱신돼요.
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes video-live-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </>
  )
}
