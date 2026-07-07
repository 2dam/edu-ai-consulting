'use client'
import { useState } from 'react'

type QcrmResult = {
  states: Record<string, number>
  labels: Record<string, string>
  readiness_score: number
  readiness_level: string
  decision_adjustment?: {
    adjusted_success_probability: number
    concurrence: number
    confidence: number
    recommendation_level: string
  }
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

const factorHelp: Record<string, { title: string; body: string; action: string }> = {
  concept_mastery: {
    title: '개념 이해',
    body: '핵심 개념을 정의하고, 비슷한 개념과 구분해서 설명할 수 있는 정도입니다.',
    action: '낮으면 정의-예시-반례를 짧은 확인 문제로 다시 묶어주세요.',
  },
  problem_interpretation: {
    title: '문제 해석',
    body: '문항 조건을 읽고, 요구하는 답과 숨은 제약을 파악하는 정도입니다.',
    action: '낮으면 조건 표시, 재진술, 함정 조건 찾기 루틴을 먼저 배치하세요.',
  },
  strategy_selection: {
    title: '전략 선택',
    body: '여러 풀이 방법 중 현재 문제에 맞는 접근을 고르는 정도입니다.',
    action: '낮으면 풀이 전 선택지를 2개 이상 비교하고 선택 이유를 말하게 하세요.',
  },
  calculation_accuracy: {
    title: '계산 정확도',
    body: '알고 있는 풀이를 실수 없이 끝까지 수행하는 정도입니다.',
    action: '낮으면 오답을 개념 오류와 계산 실수로 분리해 기록하세요.',
  },
  attention_control: {
    title: '주의 조절',
    body: '풀이 중 산만함, 긴장, 충동적 선택을 조절하는 정도입니다.',
    action: '낮으면 짧은 제한 시간 세트와 풀이 후 자기 점검을 함께 사용하세요.',
  },
  time_management: {
    title: '시간 관리',
    body: '시험 시간 안에서 문항 난도와 풀이 순서를 조절하는 정도입니다.',
    action: '낮으면 쉬운 문항 선점, 보류 표시, 재진입 시간을 훈련하세요.',
  },
}

const decisionHelp = {
  title: '판단 보정',
  body: '학습 사고 상태를 바탕으로 지금 개입안을 바로 적용할지, 작게 시험할지, 다시 설계할지 판단하는 보정값입니다.',
  action: 'pilot은 바로 전면 적용하기보다 1-2주 작은 실험으로 반응 데이터를 확인하라는 뜻입니다.',
}

const readinessHelp = {
  title: '학습 사고 상태',
  body: '개념 이해, 문제 해석, 전략 선택, 주의 조절을 묶어 본 현재 학습 준비도입니다.',
  action: 'developing이면 강점은 유지하되 가장 약한 연결고리 1-2개만 먼저 개입하세요.',
}

export default function QcrmPanel({ result }: { result: QcrmResult | null }) {
  const [selectedKey, setSelectedKey] = useState('readiness')

  if (!result) return null

  const color = levelColor[result.readiness_level] || '#3b82f6'
  const entries = Object.entries(result.states)
  const adjustment = result.decision_adjustment
  const selectedHelp =
    selectedKey === 'readiness'
      ? readinessHelp
      : selectedKey === 'decision'
        ? decisionHelp
        : factorHelp[selectedKey] || {
            title: result.labels[selectedKey] || selectedKey,
            body: '이 항목은 QCRM 학습 사고 상태를 구성하는 진단 지표입니다.',
            action: '낮은 항목부터 짧은 개입을 배치하고 2주 단위로 다시 확인하세요.',
          }

  return (
    <div style={{
      position: 'absolute',
      right: 16,
      top: 252,
      width: 240,
      // 우하단 "실시간 교육 뉴스" 패널(bottom:20, maxHeight:220)과 겹치지 않도록
      // 그 높이(220) + 여백(20) + 간격(20)만큼 아래쪽을 비워둔다.
      maxHeight: 'calc(100vh - 512px)',
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

      <button
        type="button"
        onClick={() => setSelectedKey('readiness')}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          margin: '0 0 10px',
          padding: 0,
          border: 0,
          background: 'transparent',
          color: 'inherit',
          cursor: 'pointer',
          font: 'inherit',
          textAlign: 'left',
        }}
        title="학습 사고 상태 설명 보기"
      >
        <div style={{ fontSize: 13, fontWeight: 700 }}>학습 사고 상태</div>
        <div style={{ color, fontSize: 18, fontWeight: 800 }}>{Math.round(result.readiness_score * 100)}</div>
      </button>

      <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.08)', marginBottom: 12 }}>
        <div style={{ height: '100%', width: `${Math.round(result.readiness_score * 100)}%`, background: color, borderRadius: 3 }} />
      </div>

      {adjustment && (
        <>
          <button
            type="button"
            onClick={() => setSelectedKey('decision')}
            style={{
              width: '100%',
              padding: 0,
              border: 0,
              background: 'transparent',
              cursor: 'pointer',
              textAlign: 'left',
              font: 'inherit',
            }}
            title="판단 보정 설명 보기"
          >
            <div style={{ fontSize: 10, color: selectedKey === 'decision' ? '#22c55e' : '#64748b', marginBottom: 6 }}>판단 보정</div>
          </button>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '5px 8px', fontSize: 11 }}>
            <span style={{ color: '#94a3b8' }}>개입안 적합도</span>
            <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>
              {Math.round(adjustment.adjusted_success_probability * 100)}%
            </span>
            <span style={{ color: '#94a3b8' }}>추천 모드</span>
            <span style={{ color, fontWeight: 700 }}>{adjustment.recommendation_level}</span>
            <span style={{ color: '#94a3b8' }}>신뢰도</span>
            <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>
              {Math.round(adjustment.confidence * 100)}%
            </span>
          </div>
          <div style={{ height: 4, borderRadius: 3, background: 'rgba(255,255,255,0.08)', marginTop: 8 }}>
            <div
              style={{
                height: '100%',
                width: `${Math.round(adjustment.adjusted_success_probability * 100)}%`,
                background: color,
                borderRadius: 3,
              }}
            />
          </div>
          <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '12px 0' }} />
        </>
      )}

      {entries.map(([key, value]) => (
        <button
          key={key}
          type="button"
          onClick={() => setSelectedKey(key)}
          style={{
            width: '100%',
            margin: '0 0 8px',
            padding: selectedKey === key ? '5px 6px' : '0',
            border: selectedKey === key ? '1px solid rgba(34,197,94,0.36)' : '1px solid transparent',
            borderRadius: 6,
            background: selectedKey === key ? 'rgba(34,197,94,0.08)' : 'transparent',
            cursor: 'pointer',
            font: 'inherit',
            textAlign: 'left',
            color: 'inherit',
          }}
          title={`${factorHelp[key]?.title || result.labels[key] || key} 설명 보기`}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
            <span style={{ color: selectedKey === key ? '#e2e8f0' : '#94a3b8' }}>{result.labels[key] || key}</span>
            <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>{Math.round(value * 100)}%</span>
          </div>
          <div style={{ height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.08)' }}>
            <div style={{ height: '100%', width: `${Math.round(value * 100)}%`, borderRadius: 2, background: value < 0.55 ? '#ef4444' : value < 0.7 ? '#eab308' : '#22c55e' }} />
          </div>
        </button>
      ))}

      <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '12px 0' }} />

      <div style={{ border: '1px solid rgba(148,163,184,0.18)', borderRadius: 6, padding: '9px 10px', background: 'rgba(15,23,42,0.42)', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
          <span style={{ width: 16, height: 16, borderRadius: 8, border: '1px solid rgba(34,197,94,0.55)', color: '#22c55e', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800 }}>i</span>
          <span style={{ fontSize: 11.5, fontWeight: 800, color: '#e2e8f0' }}>{selectedHelp.title}</span>
        </div>
        <div style={{ fontSize: 10.5, lineHeight: 1.45, color: '#94a3b8', marginBottom: 6 }}>
          {selectedHelp.body}
        </div>
        <div style={{ fontSize: 10.5, lineHeight: 1.45, color: '#cbd5e1' }}>
          {selectedHelp.action}
        </div>
      </div>

      <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6 }}>우선 개입 지점</div>
      {result.weakest_links.map(item => (
        <button
          key={item.factor}
          type="button"
          onClick={() => setSelectedKey(item.factor)}
          style={{
            width: '100%',
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 11,
            margin: '0 0 4px',
            padding: '2px 0',
            border: 0,
            background: 'transparent',
            color: 'inherit',
            cursor: 'pointer',
            font: 'inherit',
            textAlign: 'left',
          }}
          title={`${factorHelp[item.factor]?.title || item.label} 설명 보기`}
        >
          <span>{item.label}</span>
          <span style={{ color: '#ef4444' }}>{Math.round(item.score * 100)}%</span>
        </button>
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
