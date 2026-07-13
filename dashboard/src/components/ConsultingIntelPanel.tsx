'use client'

import { useMemo, useState } from 'react'
import type { AcademyNode, EducationFacility } from '@/lib/data'

type Scenario = 'consultant' | 'parent' | 'academy'

const scenarioLabel: Record<Scenario, string> = {
  consultant: '컨설턴트',
  parent: '학부모',
  academy: '학원',
}

const briefs: Record<Scenario, string[]> = {
  consultant: [
    '상담은 지역 수요, 학원 밀도, 학생 목표를 먼저 맞춘 뒤 오프라인/온라인 경로를 나눠 제안합니다.',
    '첫 4주는 출결, 과제 완수율, 소단원 퀴즈 추세를 추적해 추천 경로를 보정합니다.',
  ],
  parent: [
    '통학 시간이 30분을 넘으면 학습 지속성이 낮아질 수 있어 근거리 후보를 우선 비교합니다.',
    '학원 로고보다 같은 학년·같은 목표군의 변화 기록과 피드백 체계를 확인합니다.',
  ],
  academy: [
    '지역 수요가 높고 시설 데이터가 충분한 권역은 전환기 프로그램을 상품화하기 좋습니다.',
    '가격 인상 전에는 과목별 경쟁 밀도와 학부모 관심 키워드 변화를 함께 봐야 합니다.',
  ],
}

function barColor(value: number) {
  if (value >= 78) return '#22c55e'
  if (value >= 56) return '#eab308'
  return '#ef4444'
}

export default function ConsultingIntelPanel({
  regions,
  facilities,
}: {
  regions: AcademyNode[]
  facilities: EducationFacility[]
}) {
  const [scenario, setScenario] = useState<Scenario>('consultant')
  const [regionId, setRegionId] = useState(regions[0]?.id || 'gangnam')

  const region = regions.find(item => item.id === regionId) || regions[0]

  const localFacilities = useMemo(() => {
    if (!region) return []
    return facilities.filter(item => {
      const data = item.data
      return data.region?.includes(region.name) || data.address?.includes(region.name)
    })
  }, [facilities, region])

  if (!region) return null

  const facilityCount = localFacilities.length || facilities.length
  const marketDemand = Math.min(96, Math.round(region.gap_index * 58 + Math.min(region.academy_count / 45, 38)))
  const evidenceDepth = Math.min(94, Math.round(Math.min(region.academy_count / 60, 50) + Math.min(facilityCount * 5, 44)))
  const advisoryRisk = Math.max(14, Math.min(88, Math.round(region.gap_index * 72 + (region.tier === 'S' ? 10 : 0))))
  const cards = [
    ['수요', marketDemand],
    ['근거', evidenceDepth],
    ['리스크', advisoryRisk],
  ] as const

  return (
    <section style={{
      background: 'rgba(10,12,16,0.88)',
      border: '1px solid rgba(20,184,166,0.28)',
      borderRadius: 8,
      padding: '12px 14px',
      color: '#e2e8f0',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 12px 32px rgba(0,0,0,0.25)',
    }}>
      <div style={{ fontSize: 10, color: '#5eead4', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 7 }}>
        Fig. 1 Extension
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
          {regions.slice(0, 10).map(item => (
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

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>온톨로지 연결</div>
      <div style={{ fontSize: 11, lineHeight: 1.55, color: '#cbd5e1', marginBottom: 10 }}>
        {`${region.region} ${region.name} -> 학원 ${region.academy_count.toLocaleString()}개 -> 공식 시설 ${facilityCount.toLocaleString()}건 -> 상담 시나리오`}
      </div>

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>추천 근거 배합</div>
      <div style={{ fontSize: 10.5, lineHeight: 1.5, color: '#94a3b8', marginBottom: 9 }}>
        거리 20% · 학습 프로필 30% · 비용 15% · 지역 성과 프록시 25% · 출처 신뢰도 10%
      </div>

      {briefs[scenario].map((item, index) => (
        <div key={item} style={{ display: 'flex', gap: 7, fontSize: 11, lineHeight: 1.45, marginBottom: 6 }}>
          <span style={{ color: '#5eead4', fontWeight: 900 }}>{index + 1}</span>
          <span>{item}</span>
        </div>
      ))}
    </section>
  )
}
