import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

const SAMPLE_PROFILE = {
  concept_mastery: 0.62,
  problem_interpretation: 0.48,
  strategy_selection: 0.42,
  calculation_accuracy: 0.74,
  attention_control: 0.52,
  time_management: 0.45,
}

function clamp(value: number, low = 0.03, high = 0.97) {
  return Math.max(low, Math.min(high, value))
}

function round(value: number, digits = 3) {
  const scale = 10 ** digits
  return Math.round(value * scale) / scale
}

function withDecisionAdjustment(data: any) {
  if (data?.decision_adjustment) return data

  const states = data?.states || SAMPLE_PROFILE
  const contextSupport = clamp(
    0.35 * (states.concept_mastery ?? SAMPLE_PROFILE.concept_mastery) +
    0.30 * (states.problem_interpretation ?? SAMPLE_PROFILE.problem_interpretation) +
    0.20 * (states.attention_control ?? SAMPLE_PROFILE.attention_control) +
    0.15 * (states.time_management ?? SAMPLE_PROFILE.time_management)
  )
  const successGivenSupported = clamp(
    0.35 * (states.strategy_selection ?? SAMPLE_PROFILE.strategy_selection) +
    0.30 * (states.calculation_accuracy ?? SAMPLE_PROFILE.calculation_accuracy) +
    0.20 * (states.concept_mastery ?? SAMPLE_PROFILE.concept_mastery) +
    0.15 * (states.attention_control ?? SAMPLE_PROFILE.attention_control)
  )
  const successGivenUnsupported = clamp(
    0.40 * (states.concept_mastery ?? SAMPLE_PROFILE.concept_mastery) +
    0.25 * (states.problem_interpretation ?? SAMPLE_PROFILE.problem_interpretation) +
    0.20 * (states.calculation_accuracy ?? SAMPLE_PROFILE.calculation_accuracy) +
    0.15 * (states.time_management ?? SAMPLE_PROFILE.time_management)
  )
  const adjustedSuccess = clamp(
    contextSupport * successGivenSupported +
    (1 - contextSupport) * successGivenUnsupported
  )
  const confidence = clamp(0.82 - Math.abs(successGivenSupported - successGivenUnsupported) * 0.4)

  return {
    ...data,
    decision_adjustment: {
      inputs: {
        context_support: round(contextSupport, 4),
        success_given_supported: round(successGivenSupported, 4),
        success_given_unsupported: round(successGivenUnsupported, 4),
      },
      classical_success_probability: round(adjustedSuccess, 4),
      adjusted_success_probability: round(adjustedSuccess, 4),
      confidence: round(confidence, 4),
      concurrence: round(Math.abs(successGivenSupported - successGivenUnsupported), 4),
      recommendation_level: adjustedSuccess >= 0.72 && confidence >= 0.55 ? 'proceed' : adjustedSuccess >= 0.52 ? 'pilot' : 'redesign',
      recommendations: ['소규모 파일럿으로 시작하고 2주 단위 피드백으로 보정하세요.'],
      method_note: '',
    },
  }
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/qcrm-assessment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: SAMPLE_PROFILE, iterations: 3 }),
      signal: AbortSignal.timeout(5000),
      next: { revalidate: 30 },
    })
    if (res.ok) return NextResponse.json(withDecisionAdjustment(await res.json()))
  } catch {
    // Dashboard fallback for local preview without the FastAPI server.
  }

  return NextResponse.json(withDecisionAdjustment({
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
    decision_adjustment: {
      inputs: {
        context_support: 0.52,
        success_given_supported: 0.58,
        success_given_unsupported: 0.53,
        uncertainty_bias: 1,
        phase_shift: -0.08,
      },
      labels: {},
      classical_success_probability: 0.556,
      adjusted_success_probability: 0.556,
      shannon_entropy: 0.999,
      entanglement_witness: { real: 0.02, imag: 0 },
      concurrence: 0.04,
      confidence: 0.641,
      recommendation_level: 'pilot',
      recommendations: ['소규모 파일럿으로 시작하고 2주 단위 피드백으로 보정하세요.'],
      method_note: '',
    },
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
  }))
}
