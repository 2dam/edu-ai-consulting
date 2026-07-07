import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

// 지역별 평균 피처로 중도탈락 위험도 예측
// (실제 데이터 수집 전에는 지역 특성 기반 합성 피처 사용)
const REGION_FEATURES: Record<string, Record<string, number>> = {
  gangnam:   { attendance_rate: 0.97, assignment_avg_score: 88, midterm_score: 85, study_hours_per_week: 14, motivation_score: 4.2 },
  seocho:    { attendance_rate: 0.96, assignment_avg_score: 86, midterm_score: 83, study_hours_per_week: 13, motivation_score: 4.0 },
  songpa:    { attendance_rate: 0.94, assignment_avg_score: 82, midterm_score: 79, study_hours_per_week: 12, motivation_score: 3.8 },
  mapo:      { attendance_rate: 0.91, assignment_avg_score: 76, midterm_score: 72, study_hours_per_week: 10, motivation_score: 3.5 },
  nowon:     { attendance_rate: 0.89, assignment_avg_score: 71, midterm_score: 67, study_hours_per_week: 9,  motivation_score: 3.2 },
  busan:     { attendance_rate: 0.88, assignment_avg_score: 70, midterm_score: 66, study_hours_per_week: 9,  motivation_score: 3.1 },
  daegu:     { attendance_rate: 0.87, assignment_avg_score: 68, midterm_score: 64, study_hours_per_week: 8,  motivation_score: 3.0 },
  incheon:   { attendance_rate: 0.87, assignment_avg_score: 67, midterm_score: 63, study_hours_per_week: 8,  motivation_score: 3.0 },
  gwangju:   { attendance_rate: 0.88, assignment_avg_score: 69, midterm_score: 65, study_hours_per_week: 9,  motivation_score: 3.1 },
  daejeon:   { attendance_rate: 0.88, assignment_avg_score: 70, midterm_score: 65, study_hours_per_week: 9,  motivation_score: 3.1 },
  ulsan:     { attendance_rate: 0.85, assignment_avg_score: 65, midterm_score: 61, study_hours_per_week: 7,  motivation_score: 2.8 },
  sejong:    { attendance_rate: 0.91, assignment_avg_score: 75, midterm_score: 71, study_hours_per_week: 10, motivation_score: 3.4 },
  suwon:     { attendance_rate: 0.90, assignment_avg_score: 74, midterm_score: 70, study_hours_per_week: 10, motivation_score: 3.3 },
  changwon:  { attendance_rate: 0.84, assignment_avg_score: 63, midterm_score: 59, study_hours_per_week: 7,  motivation_score: 2.7 },
  cheongju:  { attendance_rate: 0.83, assignment_avg_score: 61, midterm_score: 57, study_hours_per_week: 6,  motivation_score: 2.6 },
  jeonju:    { attendance_rate: 0.84, assignment_avg_score: 62, midterm_score: 58, study_hours_per_week: 7,  motivation_score: 2.6 },
  chuncheon: { attendance_rate: 0.81, assignment_avg_score: 58, midterm_score: 54, study_hours_per_week: 6,  motivation_score: 2.4 },
  jeju:      { attendance_rate: 0.82, assignment_avg_score: 59, midterm_score: 55, study_hours_per_week: 6,  motivation_score: 2.5 },
  mokpo:     { attendance_rate: 0.79, assignment_avg_score: 55, midterm_score: 51, study_hours_per_week: 5,  motivation_score: 2.2 },
  pohang:    { attendance_rate: 0.80, assignment_avg_score: 56, midterm_score: 52, study_hours_per_week: 5,  motivation_score: 2.3 },
}

export async function GET() {
  const results: Record<string, any> = {}

  await Promise.all(
    Object.entries(REGION_FEATURES).map(async ([regionId, features]) => {
      try {
        const res = await fetch(`${BACKEND}/predict-dropout-risk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ student_features: features }),
          signal: AbortSignal.timeout(5000),
        })
        if (res.ok) {
          const data = await res.json()
          results[regionId] = {
            risk_probability: data.dropout_risk_probability,
            predicted_label: data.predicted_label,
            top_factor: data.feature_contributions?.[0]?.feature || null,
          }
        }
      } catch {
        // 백엔드 미연결 시 피처 기반 단순 추정
        const avg = (features.attendance_rate * 40 + features.motivation_score / 5 * 40 + features.midterm_score / 100 * 20)
        results[regionId] = {
          risk_probability: Math.max(0.02, Math.min(0.95, 1 - avg / 100)),
          predicted_label: avg < 50 ? 'at_risk' : 'on_track',
          top_factor: features.attendance_rate < 0.85 ? '출석률' : '동기점수',
        }
      }
    })
  )

  return NextResponse.json({ dropout_risks: results, updated_at: new Date().toISOString() })
}
