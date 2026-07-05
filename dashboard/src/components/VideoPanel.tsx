'use client'
import { useState } from 'react'

const VIDEO_TOPICS = [
  { label: '교육 뉴스 실시간', q: '대한민국 교육 뉴스 실시간' },
  { label: '입시 컨설팅', q: '2026 입시 컨설팅 설명회' },
  { label: 'EBS 수능 강의', q: 'EBSi 수능 강의' },
  { label: '교육정책 브리핑', q: '교육부 정책 브리핑 라이브' },
  { label: '유학 컨설팅', q: '해외 유학 컨설팅 세미나' },
]

export default function VideoPanel() {
  const [open, setOpen] = useState(false)
  const [activeTopic, setActiveTopic] = useState(0)
  const [loaded, setLoaded] = useState(false)

  const handleToggle = () => {
    setOpen(o => !o)
    setLoaded(true)
  }

  const videoSrc = loaded
    ? `https://www.youtube.com/embed?listType=search&list=${encodeURIComponent(VIDEO_TOPICS[activeTopic].q)}`
    : ''

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

            <iframe
              src={videoSrc}
              allow="autoplay; encrypted-media"
              allowFullScreen
              style={{ width: '100%', aspectRatio: '16 / 9', border: 'none', borderRadius: 8, background: '#000' }}
            />

            <div style={{ fontSize: 10, color: '#64748b', marginTop: 8, lineHeight: 1.6 }}>
              YouTube 실시간 검색 결과를 임베드합니다. 주제를 바꾸면 관련 최신/라이브 영상으로
              갱신돼요. 특정 영상이 재생되지 않으면 채널이 현재 라이브 중이 아닐 수 있어요.
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes video-live-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </>
  )
}
