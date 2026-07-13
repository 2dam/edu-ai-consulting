'use client'

import { useMemo, useState } from 'react'
import type { AcademyNode, EducationFacility, FacilityType } from '@/lib/data'
import { FACILITY_TYPE_LABEL } from '@/lib/data'

type Scenario = 'consultant' | 'parent' | 'academy'
type OsintTool = 'search' | 'gap-calc' | 'report' | 'facility-rating'

interface ConsultingIntelPanelProps {
  regions: AcademyNode[]
  facilities: EducationFacility[]
  onOpenOsint?: (command: {
    tool: OsintTool
    regionId?: string
    facilityType?: FacilityType | '전체'
    query?: string
  }) => void
}

const scenarioLabel: Record<Scenario, string> = {
  consultant: '컨설턴트',
  parent: '학부모',
  academy: '학원',
}

const scenarioPrompt: Record<Scenario, string> = {
  consultant: '상담 대상자 분석, 비교 후보, 상담 순서를 중심으로 작성',
  parent: '통학거리, 비용, 학습 지속성, 확인해야 할 질문을 중심으로 작성',
  academy: '지역 수요, 경쟁 밀도, 신규 과목/가격 전략을 중심으로 작성',
}

function barColor(value: number) {
  if (value >= 78) return '#22c55e'
  if (value >= 56) return '#eab308'
  return '#ef4444'
}

function shortName(value?: string) {
  if (!value) return ''
  return value.length > 18 ? `${value.slice(0, 18)}...` : value
}

export default function ConsultingIntelPanel({ regions, facilities, onOpenOsint }: ConsultingIntelPanelProps) {
  const [scenario, setScenario] = useState<Scenario>('consultant')
  const [regionId, setRegionId] = useState(regions[0]?.id || 'gangnam')
  const [reportText, setReportText] = useState('')
  const [reportLoading, setReportLoading] = useState(false)
  const [errorText, setErrorText] = useState('')

  const region = regions.find(item => item.id === regionId) || regions[0]

  const localFacilities = useMemo(() => {
    if (!region) return []
    const exact = facilities.filter(item => {
      const data = item.data
      return data.region?.includes(region.name) || data.address?.includes(region.name) || data.district === region.name
    })
    return exact.length ? exact : facilities
  }, [facilities, region])

  const facilitiesByType = useMemo(() => {
    return localFacilities.reduce((acc, item) => {
      const type = item.data.facility_type
      acc[type] = (acc[type] || 0) + 1
      return acc
    }, {} as Record<FacilityType, number>)
  }, [localFacilities])

  if (!region) return null

  const academyCandidates = localFacilities
    .filter(item => item.data.facility_type === 'academy')
    .slice(0, 4)

  const recommendedFacilities = localFacilities
    .filter(item => ['academy', 'elementary', 'kindergarten', 'university'].includes(item.data.facility_type))
    .slice(0, 5)

  const facilityCount = localFacilities.length
  const academyCount = facilitiesByType.academy || region.academy_count
  const schoolCount = (facilitiesByType.elementary || 0) + (facilitiesByType.kindergarten || 0)
  const marketDemand = Math.min(96, Math.round(region.gap_index * 58 + Math.min(region.academy_count / 45, 38)))
  const evidenceDepth = Math.min(94, Math.round(Math.min(academyCount / 60, 50) + Math.min(facilityCount * 3, 44)))
  const advisoryRisk = Math.max(14, Math.min(88, Math.round(region.gap_index * 72 + (region.tier === 'S' ? 10 : 0))))
  const cards = [
    ['수요', marketDemand],
    ['근거', evidenceDepth],
    ['리스크', advisoryRisk],
  ] as const

  const recommendations =
    scenario === 'parent'
      ? [
          `${region.name}에서는 통학거리 30분 이내 후보를 먼저 고르고, 학원 ${academyCount.toLocaleString()}개 중 과목/운영시간을 좁혀 비교합니다.`,
          '시설평가정보 탭에서 공식 평가·등록상태를 확인한 뒤 상담 보고서에 근거로 넣습니다.',
        ]
      : scenario === 'academy'
        ? [
            `${region.name} 학원 밀도와 인근 학교/유치원 신호를 같이 봐서 전환기 프로그램 수요를 추정합니다.`,
            'OSINT 격차 계산기에서 경쟁 권역과 비교한 뒤 가격·과목 패키지를 조정합니다.',
          ]
        : [
            `${region.region} ${region.name}의 지역 지표, 시설평가정보, 학원 후보를 한 상담 흐름으로 묶어 제안합니다.`,
            'AI 리포트를 생성해 상담 요약, 추천 근거, 후속 확인 질문을 문서화합니다.',
          ]

  const generateReport = async () => {
    setReportLoading(true)
    setErrorText('')
    setReportText('')
    try {
      const res = await fetch('/backend/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_label: `${scenario}-${region.id}-consulting-os`,
          tier: 'STANDARD',
          profile: {
            scenario: scenarioLabel[scenario],
            request_focus: scenarioPrompt[scenario],
            region: region.region,
            district: region.name,
            academy_count: region.academy_count,
            local_facility_count: facilityCount,
            academy_candidates: academyCandidates.map(item => item.data.name),
            evidence_mix: '거리 20%, 학습 프로필 30%, 비용 15%, 지역 성과 프록시 25%, 출처 신뢰도 10%',
          },
          context_item_types: ['EducationFacilityItem', 'CurriculumItem', 'SnsPostItem'],
        }),
      })
      if (!res.ok) throw new Error(`report ${res.status}`)
      const data = await res.json()
      setReportText(data.report_text || '리포트 본문이 비어 있습니다.')
    } catch (error) {
      setErrorText('AI 리포트를 생성하지 못했습니다. OSINT 패널의 AI 리포트 탭에서 백엔드 상태를 함께 확인하세요.')
    } finally {
      setReportLoading(false)
    }
  }

  const actionButton = (label: string, onClick: () => void) => (
    <button
      onClick={onClick}
      style={{
        border: '1px solid rgba(20,184,166,0.35)',
        borderRadius: 5,
        padding: '6px 7px',
        background: 'rgba(20,184,166,0.12)',
        color: '#5eead4',
        fontSize: 10,
        fontWeight: 800,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  )

  return (
    <section style={{
      background: 'rgba(10,12,16,0.9)',
      border: '1px solid rgba(20,184,166,0.28)',
      borderRadius: 8,
      padding: '12px 14px',
      color: '#e2e8f0',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 12px 32px rgba(0,0,0,0.25)',
    }}>
      <div style={{ fontSize: 10, color: '#5eead4', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 7 }}>
        Live Consulting OS
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: 13, fontWeight: 800 }}>교육 컨설팅 OS</div>
        <select
          value={region.id}
          onChange={event => setRegionId(event.target.value)}
          style={{
            maxWidth: 112,
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#e2e8f0',
            borderRadius: 5,
            padding: '5px 6px',
            fontSize: 11,
          }}
        >
          {regions.slice(0, 20).map(item => (
            <option key={item.id} value={item.id}>{item.name}</option>
          ))}
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 10 }}>
        {cards.map(([label, value]) => (
          <div key={label} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 6, padding: 8 }}>
            <div style={{ fontSize: 10, color: '#64748b', marginBottom: 3 }}>{label}</div>
            <div style={{ color: barColor(value), fontSize: 18, fontWeight: 900 }}>{value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 5, marginBottom: 10 }}>
        {(['consultant', 'parent', 'academy'] as Scenario[]).map(item => (
          <button
            key={item}
            onClick={() => setScenario(item)}
            style={{
              border: '1px solid rgba(255,255,255,0.09)',
              borderRadius: 5,
              padding: '6px 3px',
              background: scenario === item ? 'rgba(20,184,166,0.18)' : 'rgba(255,255,255,0.035)',
              color: scenario === item ? '#5eead4' : '#94a3b8',
              fontSize: 10,
              fontWeight: 800,
              cursor: 'pointer',
            }}
          >
            {scenarioLabel[item]}
          </button>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>실시간 데이터 연결</div>
      <div style={{ fontSize: 11, lineHeight: 1.55, color: '#cbd5e1', marginBottom: 10 }}>
        {`${region.region} ${region.name} -> 학원 ${region.academy_count.toLocaleString()}개 -> 공식 시설 ${facilityCount.toLocaleString()}건 -> 학교권 ${schoolCount.toLocaleString()}건`}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 10 }}>
        {actionButton('시설평가 열기', () => onOpenOsint?.({ tool: 'facility-rating', regionId: region.id, query: region.name }))}
        {actionButton('OSINT 검색', () => onOpenOsint?.({ tool: 'search', regionId: region.id }))}
        {actionButton('격차 비교', () => onOpenOsint?.({ tool: 'gap-calc', regionId: region.id }))}
        {actionButton(reportLoading ? '생성 중...' : 'AI 리포트', generateReport)}
      </div>

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>지역/학원 추천 후보</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginBottom: 10 }}>
        {(academyCandidates.length ? academyCandidates : recommendedFacilities).slice(0, 3).map(item => (
          <button
            key={`${item.id}-${item.data.name}`}
            onClick={() => onOpenOsint?.({
              tool: 'facility-rating',
              regionId: region.id,
              facilityType: item.data.facility_type,
              query: item.data.name,
            })}
            style={{
              textAlign: 'left',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: 5,
              background: 'rgba(255,255,255,0.035)',
              color: '#cbd5e1',
              padding: '6px 7px',
              fontSize: 10.5,
              cursor: 'pointer',
            }}
          >
            <strong style={{ color: '#e2e8f0' }}>{shortName(item.data.name)}</strong>
            <span style={{ color: '#64748b' }}> · {FACILITY_TYPE_LABEL[item.data.facility_type]}</span>
          </button>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>컨설팅 브리프</div>
      {recommendations.map((item, index) => (
        <div key={item} style={{ display: 'flex', gap: 7, fontSize: 11, lineHeight: 1.45, marginBottom: 6 }}>
          <span style={{ color: '#5eead4', fontWeight: 900 }}>{index + 1}</span>
          <span>{item}</span>
        </div>
      ))}

      {(reportText || errorText) && (
        <div style={{
          marginTop: 9,
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 6,
          background: 'rgba(255,255,255,0.035)',
          padding: 9,
          maxHeight: 180,
          overflowY: 'auto',
          whiteSpace: 'pre-wrap',
          fontSize: 10.5,
          lineHeight: 1.55,
          color: errorText ? '#fca5a5' : '#cbd5e1',
        }}>
          {errorText || reportText}
        </div>
      )}
    </section>
  )
}
