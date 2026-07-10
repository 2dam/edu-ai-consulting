'use client'
import { useEffect, useState } from 'react'

type Questions = { academy_name: string; campaign_title: string; is_active: boolean }

const RATING_QUESTIONS: { key: keyof RatingAnswers; label: string }[] = [
  { key: 'class_satisfaction', label: '수업 만족도' },
  { key: 'teacher_satisfaction', label: '강사(선생님) 만족도' },
  { key: 'homework_mgmt', label: '숙제 관리' },
  { key: 'counseling_satisfaction', label: '상담 만족도' },
  { key: 'improvement_felt', label: '성적 향상 체감' },
  { key: 'price_satisfaction', label: '가격 대비 만족도' },
]

type RatingAnswers = {
  class_satisfaction: number; teacher_satisfaction: number; homework_mgmt: number
  counseling_satisfaction: number; improvement_felt: number; price_satisfaction: number
}

function getClientFingerprint(): string {
  const key = 'eduintel_survey_fp'
  let fp = localStorage.getItem(key)
  if (!fp) {
    fp = crypto.randomUUID()
    localStorage.setItem(key, fp)
  }
  return fp
}

function RatingPicker({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          style={{
            width: 38, height: 38, borderRadius: 6, border: `1px solid ${value === n ? '#7c5cff' : '#D8D3C4'}`,
            background: value === n ? '#7c5cff' : '#fff', color: value === n ? '#fff' : '#2A2720',
            fontSize: 14, fontWeight: 700, cursor: 'pointer',
          }}
        >{n}</button>
      ))}
    </div>
  )
}

export default function SurveyFormClient({ token }: { token: string }) {
  const [questions, setQuestions] = useState<Questions | null>(null)
  const [loadError, setLoadError] = useState('')
  const [respondentType, setRespondentType] = useState<'parent' | 'student'>('parent')
  const [ratings, setRatings] = useState<RatingAnswers>({
    class_satisfaction: 0, teacher_satisfaction: 0, homework_mgmt: 0,
    counseling_satisfaction: 0, improvement_felt: 0, price_satisfaction: 0,
  })
  const [nps, setNps] = useState<number | null>(null)
  const [renewalIntent, setRenewalIntent] = useState<boolean | null>(null)
  const [freeText, setFreeText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`/api/reputation/surveys/${token}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data?.detail || '설문을 불러오지 못했습니다')
        setQuestions(data)
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : '설문을 불러오지 못했습니다'))
  }, [token])

  const allRated = Object.values(ratings).every((v) => v > 0) && nps !== null && renewalIntent !== null

  async function submit() {
    if (!allRated || submitting) return
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(`/api/reputation/surveys/${token}/responses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          respondent_type: respondentType,
          client_fingerprint: getClientFingerprint(),
          answers: { ...ratings, nps, renewal_intent: renewalIntent, free_text: freeText || null },
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `제출 실패 (${res.status})`)
      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : '제출 중 오류가 발생했습니다')
    } finally {
      setSubmitting(false)
    }
  }

  const wrap: React.CSSProperties = {
    fontFamily: "'Noto Sans KR', -apple-system, sans-serif", background: '#F1EFE8',
    minHeight: '100vh', padding: '24px 16px',
  }
  const box: React.CSSProperties = { maxWidth: 480, margin: '0 auto' }
  const card: React.CSSProperties = { background: '#fff', border: '1px solid #E4E0D5', borderRadius: 8, padding: 20, marginBottom: 16 }

  if (loadError) {
    return <div style={wrap}><div style={box}><div style={{ ...card, color: '#8C2F26' }}>{loadError}</div></div></div>
  }
  if (!questions) {
    return <div style={wrap}><div style={box}><div style={card}>불러오는 중…</div></div></div>
  }
  if (!questions.is_active) {
    return <div style={wrap}><div style={box}><div style={card}>이 설문은 마감되었습니다. 참여에 감사드립니다.</div></div></div>
  }
  if (submitted) {
    return (
      <div style={wrap}><div style={box}>
        <div style={{ ...card, textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>✓</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#1D1B16' }}>소중한 의견 감사합니다</div>
          <div style={{ fontSize: 13, color: '#6B6558', marginTop: 6 }}>응답이 정상적으로 제출되었습니다.</div>
        </div>
      </div></div>
    )
  }

  return (
    <div style={wrap}>
      <div style={box}>
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 12, color: '#7c5cff', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>{questions.academy_name}</div>
          <h1 style={{ fontFamily: "Georgia, 'Noto Serif KR', serif", fontSize: 22, margin: '4px 0 0', color: '#1D1B16' }}>{questions.campaign_title}</h1>
        </div>

        <div style={card}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#5B5342', marginBottom: 10 }}>응답자 구분</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {(['parent', 'student'] as const).map((t) => (
              <button
                key={t} type="button" onClick={() => setRespondentType(t)}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 6, border: `1px solid ${respondentType === t ? '#7c5cff' : '#D8D3C4'}`,
                  background: respondentType === t ? '#7c5cff' : '#fff', color: respondentType === t ? '#fff' : '#2A2720',
                  fontSize: 13.5, fontWeight: 700, cursor: 'pointer',
                }}
              >{t === 'parent' ? '학부모' : '학생'}</button>
            ))}
          </div>
        </div>

        <div style={card}>
          {RATING_QUESTIONS.map(({ key, label }) => (
            <div key={key} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13.5, color: '#2A2720', marginBottom: 8 }}>{label}</div>
              <RatingPicker value={ratings[key]} onChange={(v) => setRatings((prev) => ({ ...prev, [key]: v }))} />
            </div>
          ))}
        </div>

        <div style={card}>
          <div style={{ fontSize: 13.5, color: '#2A2720', marginBottom: 8 }}>주변에 이 학원을 추천할 의향이 있나요? (0~10)</div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {Array.from({ length: 11 }, (_, n) => n).map((n) => (
              <button
                key={n} type="button" onClick={() => setNps(n)}
                style={{
                  width: 30, height: 30, borderRadius: 5, border: `1px solid ${nps === n ? '#7c5cff' : '#D8D3C4'}`,
                  background: nps === n ? '#7c5cff' : '#fff', color: nps === n ? '#fff' : '#2A2720',
                  fontSize: 12, fontWeight: 700, cursor: 'pointer',
                }}
              >{n}</button>
            ))}
          </div>

          <div style={{ fontSize: 13.5, color: '#2A2720', margin: '16px 0 8px' }}>다음 학기에도 재등록할 의향이 있나요?</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {[{ v: true, label: '예' }, { v: false, label: '아니오' }].map(({ v, label }) => (
              <button
                key={label} type="button" onClick={() => setRenewalIntent(v)}
                style={{
                  flex: 1, padding: '9px 0', borderRadius: 6, border: `1px solid ${renewalIntent === v ? '#7c5cff' : '#D8D3C4'}`,
                  background: renewalIntent === v ? '#7c5cff' : '#fff', color: renewalIntent === v ? '#fff' : '#2A2720',
                  fontSize: 13.5, fontWeight: 700, cursor: 'pointer',
                }}
              >{label}</button>
            ))}
          </div>

          <div style={{ fontSize: 13.5, color: '#2A2720', margin: '16px 0 8px' }}>자유의견 (선택)</div>
          <textarea
            value={freeText} onChange={(e) => setFreeText(e.target.value)} rows={3}
            placeholder="개선되었으면 하는 점이나 좋았던 점을 자유롭게 적어주세요"
            style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #D8D3C4', borderRadius: 6, padding: 10, fontSize: 13.5, fontFamily: 'inherit', resize: 'vertical' }}
          />
        </div>

        {error && <div style={{ color: '#8C2F26', fontSize: 13, marginBottom: 12 }}>{error}</div>}

        <button
          onClick={submit}
          disabled={!allRated || submitting}
          style={{
            width: '100%', background: !allRated || submitting ? '#B8B2A0' : '#1D1B16', color: '#fff', border: 'none',
            borderRadius: 6, padding: '13px 0', fontSize: 14.5, fontWeight: 700,
            cursor: !allRated || submitting ? 'default' : 'pointer',
          }}
        >{submitting ? '제출 중…' : '제출하기'}</button>
      </div>
    </div>
  )
}
