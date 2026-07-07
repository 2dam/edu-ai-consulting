import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

const SAMPLE_PROFILE = {
  concept_mastery: 0.62,
  problem_interpretation: 0.48,
  strategy_selection: 0.42,
  calculation_accuracy: 0.74,
  attention_control: 0.52,
  time_management: 0.45,
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/qcrm-assessment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: SAMPLE_PROFILE, iterations: 3 }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 30 },
    })
    if (res.ok) return NextResponse.json(await res.json())
  } catch {
    // Dashboard fallback for local preview without the FastAPI server.
  }

  return NextResponse.json({
    states: SAMPLE_PROFILE,
    labels: {
      concept_mastery: 'Concept mastery',
      problem_interpretation: 'Problem interpretation',
      strategy_selection: 'Strategy selection',
      calculation_accuracy: 'Calculation accuracy',
      attention_control: 'Attention control',
      time_management: 'Time management',
    },
    readiness_score: 0.51,
    readiness_level: 'developing',
    weakest_links: [
      { factor: 'strategy_selection', label: 'Strategy selection', score: 0.42 },
      { factor: 'time_management', label: 'Time management', score: 0.45 },
    ],
    strongest_links: [
      { factor: 'calculation_accuracy', label: 'Calculation accuracy', score: 0.74 },
      { factor: 'concept_mastery', label: 'Concept mastery', score: 0.62 },
    ],
    recommendations: [
      '문항 조건을 다시 말하게 한 뒤 풀이 전략을 선택하게 하세요.',
      '유형별 풀이 선택지를 비교하고 선택 이유를 설명하게 하세요.',
      '짧은 시간 제한 세트와 풀이 후 자기 점검 루틴을 함께 사용하세요.',
    ],
    trace: [],
    method_note: 'FastAPI backend is not connected, so the dashboard is showing a sample Mini QCRM diagnosis.',
    narrative: '',
  })
}
