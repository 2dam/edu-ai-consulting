'use client'
import { useState } from 'react'

// 학부모On누리 (www.parents.go.kr) — 교육부 산하 국가평생교육진흥원 전국학부모지원센터가
// 운영하는 공식 학부모 교육정보 포털. 민간 서비스가 아닌 공식 출처라 이 프로젝트의
// "공식 출처 기반 정보만 다룬다"는 방침과 맞는다. 사이트 자체는 임베드(iframe)를 막아두는
// 경우가 많은 정부 사이트라, 안내 카드 + 새 탭 링크로 연결한다.
const PARENTS_PORTAL_URL = 'https://www.parents.go.kr/'

export default function ParentsPortalPanel() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'absolute',
          bottom: 20,
          left: 250,
          background: open ? 'rgba(59,130,246,0.2)' : 'rgba(10,12,16,0.88)',
          border: '1px solid rgba(59,130,246,0.4)',
          borderRadius: 20,
          color: '#60a5fa',
          padding: '6px 20px',
          fontSize: 11,
          fontWeight: 700,
          cursor: 'pointer',
          letterSpacing: '0.08em',
          backdropFilter: 'blur(12px)',
          zIndex: 10,
        }}
      >
        {open ? '▼ 학부모On누리 닫기' : '👪 학부모On누리'}
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          bottom: 70,
          left: 250,
          background: 'rgba(10,12,16,0.95)',
          border: '1px solid rgba(59,130,246,0.3)',
          borderRadius: 10,
          backdropFilter: 'blur(16px)',
          width: 320,
          overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
          zIndex: 9,
        }}>
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%', background: '#3b82f6',
              display: 'inline-block',
            }} />
            <span style={{ fontSize: 11.5, fontWeight: 700, color: '#60a5fa', letterSpacing: '0.04em' }}>
              학부모On누리
            </span>
          </div>

          <div style={{ padding: '12px 14px' }}>
            <div style={{ fontSize: 11.5, color: '#e2e8f0', lineHeight: 1.6, marginBottom: 10 }}>
              교육부·국가평생교육진흥원 전국학부모지원센터가 운영하는 공식 학부모 교육정보 포털입니다.
              자녀 교육·훈육, 학부모 코칭, 진로·입시 제도 안내 등 공신력 있는 강의·자료를 무료로 제공합니다.
            </div>
            <div style={{ fontSize: 10, color: '#64748b', lineHeight: 1.5, marginBottom: 12 }}>
              민간 리뷰가 아닌 정부·공공기관이 직접 운영하는 공식 출처입니다.
            </div>
            <a
              href={PARENTS_PORTAL_URL}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'block',
                textAlign: 'center' as const,
                color: '#0a0c10',
                background: '#3b82f6',
                borderRadius: 14,
                padding: '8px 12px',
                fontSize: 11.5,
                fontWeight: 800,
                textDecoration: 'none',
              }}
            >
              학부모On누리 바로가기 ↗
            </a>
          </div>
        </div>
      )}
    </>
  )
}
