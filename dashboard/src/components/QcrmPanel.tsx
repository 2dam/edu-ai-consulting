'use client'

type QcrmResult = {
  states: Record<string, number>
  labels: Record<string, string>
  readiness_score: number
  readiness_level: string
  weakest_links: Array<{ factor: string; label: string; score: number }>
  strongest_links: Array<{ factor: string; label: string; score: number }>
  recommendations: string[]
  method_note: string
}

const levelColor: Record<string, string> = {
  stable: '#22c55e',
  developing: '#eab308',
  needs_support: '#ef4444',
}

export default function QcrmPanel({ result }: { result: QcrmResult | null }) {
  if (!result) return null

  const color = levelColor[result.readiness_level] || '#3b82f6'
  const entries = Object.entries(result.states)

  return (
    <div style={{
      position: 'absolute',
      right: 16,
      top: 300,
      width: 240,
      // 우하단 "실시간 교육 뉴스" 패널(bottom:20, maxHeight:220)과 겹치지 않도록
      // 그 높이(220) + 여백(20) + 간격(20)만큼 아래쪽을 비워둔다.
      maxHeight: 'calc(100vh - 560px)',
      overflowY: 'auto',
      background: 'rgba(10,12,16,0.9)',
      border: '1px solid rgba(34,197,94,0.28)',
      borderRadius: 8,
      backdropFilter: 'blur(12px)',
      padding: '13px 14px',
      color: '#e2e8f0',
    }}>
      <div style={{ fontSize: 10, color: '#22c55e', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
        Mini QCRM Diagnosis
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>학습 사고 상태</div>
        <div style={{ color, fontSize: 18, fontWeight: 800 }}>{Math.round(result.readiness_score * 100)}</div>
      </div>

      <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.08)', marginBottom: 12 }}>
        <div style={{ height: '100%', width: `${Math.round(result.readiness_score * 100)}%`, background: color, borderRadius: 3 }} />
      </div>

      {entries.map(([key, value]) => (
        <div key={key} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
            <span style={{ color: '#94a3b8' }}>{result.labels[key] || key}</span>
            <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>{Math.round(value * 100)}%</span>
          </div>
          <div style={{ height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.08)' }}>
            <div style={{ height: '100%', width: `${Math.round(value * 100)}%`, borderRadius: 2, background: value < 0.55 ? '#ef4444' : value < 0.7 ? '#eab308' : '#22c55e' }} />
          </div>
        </div>
      ))}

      <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '12px 0' }} />

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>우선 개입 지점</div>
      {result.weakest_links.map(item => (
        <div key={item.factor} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
          <span>{item.label}</span>
          <span style={{ color: '#ef4444' }}>{Math.round(item.score * 100)}%</span>
        </div>
      ))}

      <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '12px 0' }} />

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>추천 상담 액션</div>
      {result.recommendations.map((item, index) => (
        <div key={index} style={{ fontSize: 11, lineHeight: 1.45, marginBottom: 7, color: '#cbd5e1' }}>
          {index + 1}. {item}
        </div>
      ))}

      <div style={{ marginTop: 10, fontSize: 9.5, lineHeight: 1.45, color: '#64748b' }}>
        {result.method_note}
      </div>
    </div>
  )
}
