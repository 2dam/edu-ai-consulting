'use client'
import { useState, useRef, useEffect } from 'react'
import type { AcademyNode, EducationFacility, FacilityType } from '@/lib/data'
import { REGION_NODES, FACILITY_TYPE_LABEL } from '@/lib/data'

interface OsintPanelProps {
  regions: AcademyNode[]
  onFlyTo?: (lat: number, lng: number, zoom: number) => void
  educationFacilities?: EducationFacility[]
  openFacilityPanelSignal?: number
  openCommandSignal?: {
    seq: number
    tool: Tool
    regionId?: string
    facilityType?: FacilityType | '전체'
    query?: string
  }
}

type Tool = 'search' | 'gap-calc' | 'report' | 'facility-rating'

const FACILITY_TYPE_FILTERS: Array<FacilityType | '전체'> = ['전체', 'daycare', 'kindergarten', 'elementary', 'academy', 'university']

export default function OsintPanel({ regions, onFlyTo, educationFacilities = [], openFacilityPanelSignal, openCommandSignal }: OsintPanelProps) {
  const [open, setOpen] = useState(false)
  const [activeTool, setActiveTool] = useState<Tool>('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<AcademyNode[]>([])
  const [compareA, setCompareA] = useState('gangnam')
  const [compareB, setCompareB] = useState('mokpo')
  const [reportRegion, setReportRegion] = useState('gangnam')
  const [reportText, setReportText] = useState('')
  const [loading, setLoading] = useState(false)
  const [facilityTypeFilter, setFacilityTypeFilter] = useState<FacilityType | '전체'>('전체')
  const [facilityQuery, setFacilityQuery] = useState('')

  // HUD의 "어린이집·유치원·학원 평가정보 보기" 버튼 클릭 시 패널을 열고 해당 탭으로 이동
  useEffect(() => {
    if (!openFacilityPanelSignal) return
    setOpen(true)
    setActiveTool('facility-rating')
  }, [openFacilityPanelSignal])

  useEffect(() => {
    if (!openCommandSignal) return
    setOpen(true)
    setActiveTool(openCommandSignal.tool)
    if (openCommandSignal.regionId) {
      setCompareA(openCommandSignal.regionId)
      setReportRegion(openCommandSignal.regionId)
      const r = regions.find(item => item.id === openCommandSignal.regionId)
      if (r) {
        setSearchQuery(r.name)
        setSearchResults([r])
        onFlyTo?.(r.lat, r.lng, 12)
      }
    }
    if (openCommandSignal.facilityType) setFacilityTypeFilter(openCommandSignal.facilityType)
    if (openCommandSignal.query !== undefined) setFacilityQuery(openCommandSignal.query)
  }, [openCommandSignal, onFlyTo, regions])

  const handleSearch = () => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return
    const results = regions.filter(r =>
      r.name.includes(searchQuery) || r.region.includes(searchQuery)
    )
    setSearchResults(results)
  }

  const regionA = regions.find(r => r.id === compareA)
  const regionB = regions.find(r => r.id === compareB)
  const gapDiff = regionA && regionB ? ((regionA.gap_index - regionB.gap_index) * 100).toFixed(1) : null
  const academyDiff = regionA && regionB ? regionA.academy_count - regionB.academy_count : null

  const facilityCountByType = educationFacilities.reduce((acc, f) => {
    acc[f.data.facility_type] = (acc[f.data.facility_type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const filteredFacilities = educationFacilities.filter(f => {
    if (facilityTypeFilter !== '전체' && f.data.facility_type !== facilityTypeFilter) return false
    const q = facilityQuery.trim()
    if (!q) return true
    return f.data.name.includes(q) || f.data.region.includes(q) || f.data.address?.includes(q)
  })

  const generateReport = async () => {
    const r = regions.find(x => x.id === reportRegion)
    if (!r) return
    setLoading(true)
    // FastAPI 백엔드에서 AI 리포트 생성
    try {
      const res = await fetch('/backend/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_label: `지역분석_${r.name}`,
          tier: 'STANDARD',
          profile: {
            region: r.region,
            name: r.name,
            academy_count: r.academy_count,
            gap_index: r.gap_index,
          },
          context_item_types: ['CurriculumItem', 'SnsPostItem'],
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setReportText(data.report_text)
      } else {
        setReportText(`[백엔드 미연결] ${r.name} 지역 분석:\n\n교육격차 지수 ${(r.gap_index * 100).toFixed(0)}/100, 학원 수 ${r.academy_count.toLocaleString()}개.\n\nOPENAI_API_KEY 설정 후 실제 AI 리포트를 생성할 수 있습니다.`)
      }
    } catch {
      const r2 = regions.find(x => x.id === reportRegion)!
      setReportText(`[오프라인 모드] ${r2.name}\n\n격차지수: ${(r2.gap_index*100).toFixed(0)}/100\n학원 수: ${r2.academy_count.toLocaleString()}개\n\n백엔드 서버를 실행하면 AI 분석이 가능합니다.`)
    }
    setLoading(false)
  }

  const s = {
    panel: {
      position: 'absolute' as const,
      bottom: 70,
      left: '50%',
      transform: 'translateX(-50%)',
      background: 'rgba(10,12,16,0.95)',
      border: '1px solid rgba(249,115,22,0.3)',
      borderRadius: 10,
      backdropFilter: 'blur(16px)',
      width: 580,
      maxHeight: '60vh',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column' as const,
      boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
    },
    tab: (active: boolean) => ({
      padding: '8px 14px',
      fontSize: 11,
      cursor: 'pointer',
      background: active ? 'rgba(249,115,22,0.15)' : 'transparent',
      color: active ? '#f97316' : '#64748b',
      borderBottom: active ? '2px solid #f97316' : '2px solid transparent',
      whiteSpace: 'nowrap' as const,
    }),
    input: {
      background: 'rgba(255,255,255,0.06)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#e2e8f0',
      padding: '7px 10px',
      fontSize: 12,
      outline: 'none',
      width: '100%',
    },
    btn: {
      background: '#f97316',
      color: '#000',
      border: 'none',
      borderRadius: 6,
      padding: '7px 14px',
      fontSize: 11,
      fontWeight: 700,
      cursor: 'pointer',
      whiteSpace: 'nowrap' as const,
    },
    label: { fontSize: 10, color: '#64748b', marginBottom: 4, display: 'block' as const },
    select: {
      background: 'rgba(255,255,255,0.06)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#e2e8f0',
      padding: '6px 8px',
      fontSize: 12,
      outline: 'none',
      width: '100%',
    },
  }

  return (
    <>
      {/* 트리거 버튼 */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'absolute',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          background: open ? 'rgba(249,115,22,0.2)' : 'rgba(10,12,16,0.88)',
          border: '1px solid rgba(249,115,22,0.4)',
          borderRadius: 20,
          color: '#f97316',
          padding: '6px 20px',
          fontSize: 11,
          fontWeight: 700,
          cursor: 'pointer',
          letterSpacing: '0.08em',
          backdropFilter: 'blur(12px)',
          zIndex: 10,
        }}
      >
        {open ? '▼ OSINT 닫기' : '▲ OSINT 분석 도구'}
      </button>

      {open && (
        <div style={s.panel}>
          {/* 탭 */}
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '0 4px' }}>
            {([
              ['search', '🔍 학원·지역 검색'],
              ['gap-calc', '📊 격차 계산기'],
              ['facility-rating', '🧸 시설 평가정보'],
              ['report', '🤖 AI 리포트'],
            ] as [Tool, string][]).map(([id, label]) => (
              <button key={id} onClick={() => setActiveTool(id)} style={s.tab(activeTool === id)}>{label}</button>
            ))}
          </div>

          <div style={{ padding: 16, overflowY: 'auto', flex: 1 }}>

            {/* ── 학원·지역 검색 ────────────────────────────────────── */}
            {activeTool === 'search' && (
              <div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  <input
                    style={s.input}
                    placeholder="지역명 검색 (예: 강남, 부산, 대전...)"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  />
                  <button style={s.btn} onClick={handleSearch}>검색</button>
                </div>
                {searchResults.length === 0 && searchQuery && (
                  <div style={{ color: '#64748b', fontSize: 11 }}>결과 없음</div>
                )}
                {searchResults.length === 0 && !searchQuery && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                    {regions.slice(0, 12).map(r => (
                      <div
                        key={r.id}
                        onClick={() => onFlyTo?.(r.lat, r.lng, 12)}
                        style={{
                          background: 'rgba(255,255,255,0.04)',
                          border: '1px solid rgba(255,255,255,0.07)',
                          borderRadius: 6,
                          padding: '8px 10px',
                          cursor: 'pointer',
                          fontSize: 11,
                        }}
                      >
                        <div style={{ fontWeight: 600, marginBottom: 3 }}>{r.name}</div>
                        <div style={{ color: '#64748b', fontSize: 10 }}>
                          학원 {r.academy_count.toLocaleString()}개 · 격차 {(r.gap_index*100).toFixed(0)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {searchResults.map(r => (
                  <div
                    key={r.id}
                    onClick={() => onFlyTo?.(r.lat, r.lng, 12)}
                    style={{
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.07)',
                      borderRadius: 6,
                      padding: '10px 12px',
                      marginBottom: 8,
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>{r.region} {r.name}</div>
                      <div style={{ color: '#64748b', fontSize: 10 }}>
                        학원 {r.academy_count.toLocaleString()}개 · 격차지수 {(r.gap_index * 100).toFixed(0)}
                      </div>
                    </div>
                    <div style={{
                      fontSize: 16, fontWeight: 800,
                      color: r.tier === 'S' ? '#f97316' : r.tier === 'A' ? '#eab308' : r.tier === 'B' ? '#3b82f6' : '#64748b'
                    }}>{r.tier}</div>
                  </div>
                ))}
              </div>
            )}

            {/* ── 격차 계산기 ───────────────────────────────────────── */}
            {activeTool === 'gap-calc' && (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                  <div>
                    <label style={s.label}>지역 A</label>
                    <select style={s.select} value={compareA} onChange={e => setCompareA(e.target.value)}>
                      {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={s.label}>지역 B</label>
                    <select style={s.select} value={compareB} onChange={e => setCompareB(e.target.value)}>
                      {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </div>
                </div>

                {regionA && regionB && (
                  <div>
                    <CompareRow label="교육격차 지수" a={`${(regionA.gap_index*100).toFixed(0)}/100`} b={`${(regionB.gap_index*100).toFixed(0)}/100`} diff={`${Number(gapDiff)>0?'+':''}${gapDiff}점`} worse={Number(gapDiff) > 0} />
                    <CompareRow label="학원 수" a={`${regionA.academy_count.toLocaleString()}개`} b={`${regionB.academy_count.toLocaleString()}개`} diff={`${academyDiff! > 0 ? '+' : ''}${academyDiff!.toLocaleString()}개`} worse={academyDiff! > 0} />

                    <div style={{ marginTop: 14, padding: 12, background: 'rgba(239,68,68,0.08)', borderRadius: 8, border: '1px solid rgba(239,68,68,0.2)' }}>
                      <div style={{ fontSize: 11, color: '#ef4444', marginBottom: 6, fontWeight: 600 }}>격차 분석 요약</div>
                      <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.7 }}>
                        {regionA.name}은 {regionB.name}보다 학원이 <strong style={{color:'#f97316'}}>{academyDiff!.toLocaleString()}개</strong> 많습니다.
                        교육격차 지수 차이는 <strong style={{color:'#ef4444'}}>{gapDiff}점</strong>으로,
                        이는 {regionB.name} 학생이 동등한 입시 정보를 얻기 위해
                        <strong style={{color:'#a855f7'}}> AI 컨설팅이 핵심 보완재</strong>임을 시사합니다.
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── 시설 평가정보 (어린이집·유치원·초등학교·학원) ───────── */}
            {activeTool === 'facility-rating' && (
              <div>
                <div style={{ fontSize: 10, color: '#64748b', marginBottom: 10, lineHeight: 1.6 }}>
                  네이버·카카오 등 민간 리뷰가 아닌, 어린이집평가제·정보공시·학원 등록현황 등
                  <strong style={{ color: '#ec4899' }}> 공식 출처 기반 평가정보</strong>만 표시합니다.
                </div>

                {educationFacilities.length > 0 && educationFacilities.every(f => f.data.is_sample) && (
                  <div style={{
                    background: 'rgba(234,179,8,0.1)', border: '1px solid rgba(234,179,8,0.3)',
                    borderRadius: 6, padding: '8px 10px', marginBottom: 10, fontSize: 10, color: '#eab308', lineHeight: 1.6,
                  }}>
                    ⚠ 아직 실제 데이터를 수집하기 전이라 화면 구성 확인용 예시 데이터를 보여주고 있습니다.
                    crawler/edu_crawler/spiders/early_education_spider.py 실행 후 실제 데이터로 교체됩니다.
                  </div>
                )}

                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' as const, marginBottom: 10 }}>
                  {FACILITY_TYPE_FILTERS.map(ft => (
                    <button
                      key={ft}
                      onClick={() => setFacilityTypeFilter(ft)}
                      style={{
                        padding: '4px 10px', fontSize: 10, borderRadius: 12, cursor: 'pointer',
                        background: facilityTypeFilter === ft ? '#ec4899' : 'rgba(255,255,255,0.06)',
                        color: facilityTypeFilter === ft ? '#000' : '#94a3b8',
                        border: '1px solid rgba(255,255,255,0.1)',
                        fontWeight: facilityTypeFilter === ft ? 700 : 400,
                      }}
                    >
                      {ft === '전체' ? '전체' : FACILITY_TYPE_LABEL[ft]}
                      {ft !== '전체' && facilityCountByType[ft] ? ` (${facilityCountByType[ft]})` : ''}
                    </button>
                  ))}
                </div>

                <input
                  style={{ ...s.input, marginBottom: 10 }}
                  placeholder="시설명·지역·주소 검색"
                  value={facilityQuery}
                  onChange={e => setFacilityQuery(e.target.value)}
                />

                <div style={{ fontSize: 10, color: '#64748b', marginBottom: 10 }}>
                  총 {educationFacilities.length.toLocaleString()}곳 수집됨 · 조회 결과 {filteredFacilities.length.toLocaleString()}곳
                </div>

                {educationFacilities.length === 0 && (
                  <div style={{ color: '#64748b', fontSize: 11, lineHeight: 1.7 }}>
                    아직 수집된 데이터가 없습니다.<br />
                    crawler/edu_crawler/spiders/early_education_spider.py 를 실행하면
                    (초등학교는 NEIS_API_KEY 발급만으로 바로 동작) 여기 표시됩니다.
                  </div>
                )}

                {educationFacilities.length > 0 && filteredFacilities.length === 0 && (
                  <div style={{ color: '#64748b', fontSize: 11 }}>조건에 맞는 시설이 없습니다.</div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 6 }}>
                  {filteredFacilities.slice(0, 50).map(f => (
                    <div
                      key={f.id}
                      style={{
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.07)',
                        borderRadius: 6,
                        padding: '8px 10px',
                        fontSize: 11,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <div style={{ fontWeight: 600 }}>{f.data.name}</div>
                        <span style={{
                          fontSize: 10, fontWeight: 700, color: '#ec4899',
                          background: 'rgba(236,72,153,0.12)', borderRadius: 3, padding: '1px 6px',
                        }}>
                          {FACILITY_TYPE_LABEL[f.data.facility_type]}
                        </span>
                      </div>
                      <div style={{ color: '#64748b', fontSize: 10 }}>
                        {f.data.region} · {f.data.address || '주소 미상'}
                      </div>
                      {(f.data.evaluation_grade || f.data.status_note) && (
                        <div style={{ marginTop: 4, fontSize: 10, color: '#94a3b8' }}>
                          {f.data.evaluation_grade && <span>평가등급: <strong style={{ color: '#22c55e' }}>{f.data.evaluation_grade}</strong></span>}
                          {f.data.evaluation_grade && f.data.status_note && ' · '}
                          {f.data.status_note && <span>등록상태: {f.data.status_note}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── AI 리포트 ─────────────────────────────────────────── */}
            {activeTool === 'report' && (
              <div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  <div style={{ flex: 1 }}>
                    <label style={s.label}>분석 지역 선택</label>
                    <select style={s.select} value={reportRegion} onChange={e => setReportRegion(e.target.value)}>
                      {regions.map(r => <option key={r.id} value={r.id}>{r.region} {r.name}</option>)}
                    </select>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <button style={s.btn} onClick={generateReport} disabled={loading}>
                      {loading ? '분석 중...' : '🤖 AI 분석'}
                    </button>
                  </div>
                </div>
                {reportText && (
                  <div style={{
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.07)',
                    borderRadius: 8,
                    padding: 12,
                    fontSize: 11,
                    lineHeight: 1.7,
                    color: '#cbd5e1',
                    whiteSpace: 'pre-wrap' as const,
                    maxHeight: 260,
                    overflowY: 'auto',
                  }}>
                    {reportText}
                  </div>
                )}
                {!reportText && (
                  <div style={{ color: '#64748b', fontSize: 11, lineHeight: 1.7 }}>
                    지역을 선택하고 [AI 분석] 버튼을 누르면<br />
                    FastAPI 백엔드가 교육격차·학원 데이터를 분석해<br />
                    해당 지역 학생을 위한 맞춤 컨설팅 인사이트를 생성합니다.
                  </div>
                )}
              </div>
            )}

          </div>
        </div>
      )}
    </>
  )
}

function CompareRow({ label, a, b, diff, worse }: { label: string; a: string; b: string; diff: string; worse: boolean }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr 1fr 80px', gap: 8, marginBottom: 8, alignItems: 'center', fontSize: 11 }}>
      <div style={{ color: '#64748b' }}>{label}</div>
      <div style={{ textAlign: 'center' as const, padding: '4px 8px', background: 'rgba(249,115,22,0.1)', borderRadius: 4, color: '#f97316' }}>{a}</div>
      <div style={{ textAlign: 'center' as const, padding: '4px 8px', background: 'rgba(59,130,246,0.1)', borderRadius: 4, color: '#3b82f6' }}>{b}</div>
      <div style={{ textAlign: 'center' as const, color: worse ? '#ef4444' : '#22c55e', fontFamily: 'monospace', fontWeight: 700 }}>{diff}</div>
    </div>
  )
}
