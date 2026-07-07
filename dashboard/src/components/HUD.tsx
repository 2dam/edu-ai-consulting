'use client'
import { useState, useEffect } from 'react'
import type { AcademyNode, GangnamAcademy, LayerId } from '@/lib/data'
import { LAYERS } from '@/lib/data'

interface HUDProps {
  regions: AcademyNode[]
  loopStatus: any
  backendCount: number
  activeLayers: Set<LayerId>
  onToggleLayer: (id: LayerId) => void
  selected: AcademyNode | GangnamAcademy | null
  news: any[]
  onOpenFacilityPanel?: () => void
  cctvCount?: number
}

function Clock() {
  const [time, setTime] = useState('')
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('ko-KR', { hour12: false }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])
  return <span style={{ fontFamily: 'monospace', color: '#22c55e' }}>{time}</span>
}

function StatBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, color: '#94a3b8', fontSize: 11 }}>
        <span>{label}</span>
        <span style={{ color }}>{value.toLocaleString()}</span>
      </div>
      <div style={{ height: 3, background: 'rgba(255,255,255,0.08)', borderRadius: 2 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 2, transition: 'width 0.8s ease' }} />
      </div>
    </div>
  )
}

export default function HUD({ regions, loopStatus, backendCount, activeLayers, onToggleLayer, selected, news, onOpenFacilityPanel, cctvCount = 0 }: HUDProps) {
  const totalAcademies = regions.reduce((s, r) => s + r.academy_count, 0)
  const maxGap = Math.max(...regions.map(r => r.gap_index))
  const minGap = Math.min(...regions.map(r => r.gap_index))
  const topRegions = [...regions].sort((a, b) => b.gap_index - a.gap_index).slice(0, 3)

  const tierBadge = (tier: string) => {
    const colors: Record<string, string> = { S: '#f97316', A: '#eab308', B: '#3b82f6', C: '#64748b' }
    return (
      <span style={{
        background: colors[tier] + '33', color: colors[tier],
        border: `1px solid ${colors[tier]}66`,
        borderRadius: 3, padding: '1px 6px', fontSize: 10, fontWeight: 700,
      }}>{tier}등급</span>
    )
  }

  const panel = {
    position: 'absolute' as const,
    background: 'rgba(10,12,16,0.88)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 8,
    backdropFilter: 'blur(12px)',
    padding: '12px 14px',
  }

  const label = { fontSize: 10, color: '#64748b', textTransform: 'uppercase' as const, letterSpacing: '0.08em', marginBottom: 6 }
  const divider = { height: 1, background: 'rgba(255,255,255,0.06)', margin: '10px 0' }

  return (
    <>
      {/* ── 상단 제목바 ──────────────────────────────────────────────── */}
      <div style={{
        ...panel,
        top: 16, left: '50%', transform: 'translateX(-50%)',
        display: 'flex', alignItems: 'center', gap: 24, padding: '8px 20px',
        borderColor: 'rgba(249,115,22,0.3)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 8px #22c55e', animation: 'pulse 2s infinite' }} />
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', color: '#f97316' }}>EDUINTEL</span>
          <span style={{ fontSize: 10, color: '#64748b' }}>/ 한국 교육 인텔리전스</span>
        </div>
        <div style={{ fontSize: 11, color: '#64748b' }}><Clock /> KST</div>
        <div style={{ fontSize: 10, color: '#64748b' }}>LIVE · {regions.length}개 지역 · {totalAcademies.toLocaleString()}개 학원</div>
      </div>

      {/* ── 좌측 패널: 통계 ──────────────────────────────────────────── */}
      <div style={{ ...panel, top: 64, left: 16, width: 220 }}>
        <div style={label}>시스템 현황</div>
        <StatBar label="수집된 데이터" value={backendCount} max={5000} color="#f97316" />
        <StatBar label="전국 학원 수" value={totalAcademies} max={100000} color="#3b82f6" />
        <StatBar label="AI 피드백 누적" value={loopStatus?.total_feedbacks || 0} max={loopStatus?.retrain_threshold || 10} color="#a855f7" />
        <div style={divider} />
        <div style={label}>교육격차 지수 (격차↑=빨강)</div>
        {topRegions.map(r => (
          <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 11 }}>
            <span>{r.name}</span>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              {tierBadge(r.tier)}
              <span style={{ color: r.gap_index > 0.7 ? '#ef4444' : '#eab308', fontFamily: 'monospace' }}>
                {(r.gap_index * 100).toFixed(0)}
              </span>
            </div>
          </div>
        ))}
        <div style={divider} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b' }}>
          <span>격차 최대</span><span style={{ color: '#ef4444' }}>{(maxGap * 100).toFixed(0)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b' }}>
          <span>격차 최소</span><span style={{ color: '#22c55e' }}>{(minGap * 100).toFixed(0)}</span>
        </div>
      </div>

      {/* ── 좌하단: 레이어 컨트롤 ────────────────────────────────────── */}
      <div style={{ ...panel, bottom: 20, left: 16, width: 220 }}>
        <div style={label}>데이터 레이어</div>
        {LAYERS.map(layer => (
          <div key={layer.id}>
            <div
              onClick={() => onToggleLayer(layer.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '5px 0', cursor: 'pointer', userSelect: 'none',
                opacity: activeLayers.has(layer.id) ? 1 : 0.4,
                transition: 'opacity 0.2s',
              }}
            >
              <div style={{
                width: 10, height: 10, borderRadius: 2,
                background: activeLayers.has(layer.id) ? layer.color : 'transparent',
                border: `1.5px solid ${layer.color}`,
                transition: 'background 0.2s',
              }} />
              <span style={{ fontSize: 11 }}>{layer.icon} {layer.label}</span>
            </div>
            {layer.id === 'cctv' && activeLayers.has('cctv') && cctvCount === 0 && (
              <div style={{ fontSize: 9.5, color: '#eab308', lineHeight: 1.5, padding: '2px 0 6px 18px' }}>
                ⚠ 잠시 CCTV를 불러올 수 없습니다 — 배포 서버 네트워크에서 ITS API
                연결이 차단된 것으로 보입니다 (조치 예정, 로컬 실행 시에는 정상 동작).
              </div>
            )}
          </div>
        ))}
        {onOpenFacilityPanel && (
          <button
            onClick={onOpenFacilityPanel}
            style={{
              marginTop: 10, width: '100%',
              background: 'rgba(236,72,153,0.15)', border: '1px solid rgba(236,72,153,0.4)',
              borderRadius: 6, color: '#ec4899', padding: '6px 8px', fontSize: 11, fontWeight: 700,
              cursor: 'pointer', textAlign: 'left' as const,
            }}
          >
            🧸 어린이집·유치원·학원 평가정보 보기 →
          </button>
        )}
      </div>

      {/* ── 우측 패널: 선택 항목 상세 ────────────────────────────────── */}
      <div style={{ ...panel, top: 64, right: 16, width: 240 }}>
        {selected ? (
          <>
            <div style={label}>선택된 항목</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>
              {'academy_count' in selected ? selected.name : selected.name}
            </div>
            {'academy_count' in selected ? (
              <>
                <div style={divider} />
                <Row label="지역" value={`${selected.region} · ${selected.name}`} />
                <Row label="학원 수" value={`${selected.academy_count.toLocaleString()}개`} color="#f97316" />
                <Row label="수능 성적 백분위" value={`상위 ${100 - selected.avg_score_rank}%`} color={selected.avg_score_rank > 85 ? '#ef4444' : '#22c55e'} />
                <Row label="교육격차 지수" value={`${(selected.gap_index * 100).toFixed(0)} / 100`} color={selected.gap_index > 0.7 ? '#ef4444' : '#eab308'} />
                <Row label="등급" value={<span>{tierBadge(selected.tier)}</span>} />
                <div style={divider} />
                <div style={{ fontSize: 10, color: '#64748b' }}>
                  격차지수 {(selected.gap_index * 100).toFixed(0)}은 강남(92) 대비{' '}
                  <span style={{ color: '#ef4444' }}>{((0.92 - selected.gap_index) * 100).toFixed(0)}점</span> 낮음
                </div>
              </>
            ) : (
              <>
                <div style={divider} />
                <Row label="과목" value={'subject' in selected ? selected.subject : ''} />
                <Row label="등급" value={<span>{'tier' in selected ? tierBadge(selected.tier) : ''}</span>} />
                {'website' in selected && selected.website && (
                  <a href={selected.website} target="_blank" rel="noreferrer"
                    style={{ display: 'block', marginTop: 8, fontSize: 10, color: '#3b82f6' }}>
                    홈페이지 →
                  </a>
                )}
              </>
            )}
          </>
        ) : (
          <>
            <div style={label}>AI 루프 상태</div>
            <Row label="활성 프롬프트" value={loopStatus?.active_prompt_variant ? `Variant ${loopStatus.active_prompt_variant}` : '—'} color="#22c55e" />
            <Row label="총 사이클" value={loopStatus?.total_loop_cycles ?? '—'} />
            <Row label="미처리 피드백" value={`${loopStatus?.unprocessed_feedbacks ?? 0} / ${loopStatus?.retrain_threshold ?? 10}`} />
            <Row label="재학습까지" value={`${loopStatus?.feedbacks_until_retrain ?? '—'}건`} color="#a855f7" />
            <div style={divider} />
            <div style={{ fontSize: 10, color: '#64748b' }}>
              지역을 클릭하면 상세 분석이 표시됩니다.
            </div>
          </>
        )}
      </div>

      {/* ── 우하단: 실시간 뉴스 ─────────────────────────────────────── */}
      <div style={{ ...panel, bottom: 20, right: 16, width: 280, maxHeight: 220, overflowY: 'auto' }}>
        <div style={label}>📡 실시간 교육 뉴스</div>
        {news.map((item, i) => (
          <div key={i} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: i < news.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
            <div style={{ fontSize: 11, lineHeight: 1.4, marginBottom: 3 }}>{item.title}</div>
            <div style={{ fontSize: 10, color: '#64748b', display: 'flex', gap: 8 }}>
              <span style={{ color: '#3b82f6' }}>{item.category}</span>
              <span>{item.source}</span>
              <span>{item.time}</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── 범례 ─────────────────────────────────────────────────────── */}
      <div style={{ ...panel, bottom: 20, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 20, padding: '6px 16px' }}>
        {[
          { label: 'S등급 (강남권)', color: '#f97316' },
          { label: 'A등급', color: '#eab308' },
          { label: 'B등급', color: '#3b82f6' },
          { label: 'C등급 (지방)', color: '#64748b' },
        ].map(({ label, color }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: '#94a3b8' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
            {label}
          </div>
        ))}
        <div style={{ width: 1, background: 'rgba(255,255,255,0.1)' }} />
        <div style={{ fontSize: 10, color: '#64748b' }}>원 크기 = 학원 수</div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </>
  )
}

function Row({ label, value, color }: { label: string; value: any; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 11 }}>
      <span style={{ color: '#64748b' }}>{label}</span>
      <span style={{ color: color || '#e2e8f0', fontWeight: 500 }}>{value}</span>
    </div>
  )
}
