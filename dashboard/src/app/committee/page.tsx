'use client'
import { useState } from 'react'

type CommitteeAgent = {
  id: string
  name: string
  category: string
  perspective: string
  priority: string
  tone: string
}

type RunResult = {
  case_type: string
  committee: CommitteeAgent[]
  opinions: Record<string, string>
  draft: string
}

const CATEGORY_COLOR: Record<string, string> = {
  '입시·진학': '#2C4A6E',
  '교육 현장': '#3E6355',
  '심리·상담': '#6B4E71',
  '정책·제도': '#5B5342',
  '산업·트렌드': '#3E5C76',
  '경험 기반': '#7A6247',
  '위기·리스크 대응': '#8C2F26',
}

function AgentBadge({ agent }: { agent: CommitteeAgent }) {
  const color = CATEGORY_COLOR[agent.category] || '#444'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      border: `1px solid ${color}33`, borderLeft: `4px solid ${color}`,
      background: '#FBFAF7', padding: '10px 14px', borderRadius: 4,
    }}>
      <span style={{
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 12, color, fontWeight: 700, minWidth: 30,
      }}>{agent.id}</span>
      <div>
        <div style={{ fontWeight: 700, fontSize: 14, color: '#1D1B16' }}>{agent.name}</div>
        <div style={{ fontSize: 11.5, color: '#6B6558' }}>{agent.category}</div>
      </div>
    </div>
  )
}

function OpinionCard({ agent, opinion }: { agent: CommitteeAgent; opinion: string }) {
  const color = CATEGORY_COLOR[agent.category] || '#444'
  return (
    <div style={{ border: '1px solid #E4E0D5', borderRadius: 6, background: '#fff', padding: 16, marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{
          fontFamily: 'ui-monospace, monospace', fontSize: 11, fontWeight: 700,
          color: '#fff', background: color, borderRadius: 3, padding: '2px 6px',
        }}>{agent.id}</span>
        <span style={{ fontWeight: 700, fontSize: 14.5, color: '#1D1B16' }}>{agent.name}</span>
      </div>
      <div style={{ fontSize: 14, lineHeight: 1.65, color: '#2A2720', whiteSpace: 'pre-wrap' }}>{opinion}</div>
    </div>
  )
}

export default function CommitteePage() {
  const [caseText, setCaseText] = useState('')
  const [stage, setStage] = useState<'idle' | 'draft' | 'final'>('idle')
  const [result, setResult] = useState<RunResult | null>(null)
  const [finalReport, setFinalReport] = useState('')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function runCommittee() {
    if (!caseText.trim() || busy) return
    setError('')
    setResult(null)
    setFinalReport('')
    setFeedback('')
    setBusy(true)
    try {
      const res = await fetch('/api/committee/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_text: caseText }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `요청 실패 (${res.status})`)
      setResult(data)
      setStage('draft')
    } catch (err) {
      setError(err instanceof Error ? err.message : '위원회 소집 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  async function submitFeedback() {
    if (!feedback.trim() || busy || !result) return
    setBusy(true)
    setError('')
    try {
      const res = await fetch('/api/committee/revise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft: result.draft, feedback }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `요청 실패 (${res.status})`)
      setFinalReport(data.final_report)
      setStage('final')
    } catch (err) {
      setError(err instanceof Error ? err.message : '최종안 생성 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  function reset() {
    setCaseText('')
    setStage('idle')
    setResult(null)
    setFinalReport('')
    setFeedback('')
    setError('')
  }

  return (
    <div style={{
      fontFamily: "'Noto Sans KR', -apple-system, sans-serif",
      background: '#F1EFE8', minHeight: '100vh', padding: '32px 16px',
    }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{
            fontFamily: 'ui-monospace, monospace', fontSize: 11.5, letterSpacing: 1.5,
            color: '#7c5cff', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6,
          }}>EduIntelligence Panel · 사안접수</div>
          <h1 style={{
            fontFamily: "Georgia, 'Noto Serif KR', serif", fontSize: 26, margin: 0,
            color: '#1D1B16', fontWeight: 700, letterSpacing: -0.3,
          }}>30인 전문가 풀 · AI 위원회 소집</h1>
          <div style={{ fontSize: 13.5, color: '#6B6558', marginTop: 6 }}>
            사안을 접수하면 30인 풀에서 관련 위원을 자동 소집해 토의 → 초안 → 피드백 → 최종안을 산출합니다.
          </div>
        </div>

        <div style={{ background: '#fff', border: '1px solid #E4E0D5', borderRadius: 6, padding: 18, marginBottom: 20 }}>
          <label style={{ fontSize: 12.5, fontWeight: 700, color: '#5B5342', display: 'block', marginBottom: 8 }}>
            사안 내용
          </label>
          <textarea
            value={caseText}
            onChange={(e) => setCaseText(e.target.value)}
            placeholder="예: 중2 학생이 SNS 단체방에서 지속적으로 괴롭힘을 당했다는 신고가 접수되었습니다. 학부모가 학교에 조치를 요청한 상태입니다."
            rows={4}
            disabled={busy}
            style={{
              width: '100%', boxSizing: 'border-box', border: '1px solid #D8D3C4', borderRadius: 4,
              padding: 10, fontSize: 14, fontFamily: 'inherit', resize: 'vertical',
            }}
          />
          <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
            <button
              onClick={runCommittee}
              disabled={busy || !caseText.trim()}
              style={{
                background: busy ? '#B8B2A0' : '#1D1B16', color: '#fff', border: 'none',
                borderRadius: 4, padding: '10px 18px', fontSize: 13.5, fontWeight: 700,
                cursor: busy ? 'default' : 'pointer',
              }}
            >{busy && stage !== 'draft' ? '위원회 소집 중… (최대 1분)' : '위원회 소집'}</button>
            {stage !== 'idle' && (
              <button onClick={reset} disabled={busy} style={{
                background: 'transparent', color: '#6B6558', border: '1px solid #D8D3C4',
                borderRadius: 4, padding: '10px 18px', fontSize: 13.5, cursor: busy ? 'default' : 'pointer',
              }}>새 사안</button>
            )}
          </div>
          {error && <div style={{ color: '#8C2F26', fontSize: 13, marginTop: 8 }}>{error}</div>}
        </div>

        {result && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span style={{
                fontSize: 11.5, fontWeight: 700, padding: '3px 9px', borderRadius: 3,
                background: result.case_type === '위기 대응형' ? '#8C2F2618' : '#2C4A6E18',
                color: result.case_type === '위기 대응형' ? '#8C2F26' : '#2C4A6E',
              }}>{result.case_type}</span>
              <span style={{ fontSize: 13, color: '#6B6558' }}>소집 위원 {result.committee.length}인</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {result.committee.map((a) => <AgentBadge key={a.id} agent={a} />)}
            </div>
          </div>
        )}

        {result && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#5B5342', marginBottom: 10 }}>위원별 토의 발언</div>
            {result.committee.map((a) => (
              <OpinionCard key={a.id} agent={a} opinion={result.opinions[a.id] || ''} />
            ))}
          </div>
        )}

        {result && (
          <div style={{ background: '#fff', border: '1px solid #E4E0D5', borderRadius: 6, padding: 20, marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#5B5342', marginBottom: 10 }}>
              {stage === 'final' ? '최종 확정본' : '초안 보고서'}
            </div>
            <div style={{
              fontSize: 14, lineHeight: 1.7, color: '#2A2720', whiteSpace: 'pre-wrap',
              fontFamily: "Georgia, 'Noto Serif KR', serif",
            }}>{stage === 'final' ? finalReport : result.draft}</div>

            {stage === 'draft' && (
              <div style={{ marginTop: 18, borderTop: '1px dashed #D8D3C4', paddingTop: 16 }}>
                <label style={{ fontSize: 12.5, fontWeight: 700, color: '#5B5342', display: 'block', marginBottom: 8 }}>
                  컨설턴트 피드백
                </label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="예: 변호사 의견 비중을 낮추고 학부모 대응 매뉴얼을 더 추가해줘"
                  rows={3}
                  disabled={busy}
                  style={{
                    width: '100%', boxSizing: 'border-box', border: '1px solid #D8D3C4', borderRadius: 4,
                    padding: 10, fontSize: 14, fontFamily: 'inherit', resize: 'vertical',
                  }}
                />
                <button
                  onClick={submitFeedback}
                  disabled={busy || !feedback.trim()}
                  style={{
                    marginTop: 10, background: busy ? '#B8B2A0' : '#1D1B16', color: '#fff', border: 'none',
                    borderRadius: 4, padding: '10px 18px', fontSize: 13.5, fontWeight: 700,
                    cursor: busy ? 'default' : 'pointer',
                  }}
                >{busy ? '반영 중…' : '피드백 반영해 최종안 생성'}</button>
              </div>
            )}
          </div>
        )}

        <div style={{ fontSize: 11.5, color: '#9A9384', lineHeight: 1.6, textAlign: 'center', marginTop: 8 }}>
          본 위원회는 가상 전문가 페르소나의 참고 자료이며, 법적 효력이나 공식 자격을 가진 판단이 아닙니다.
          위기 대응형 사안은 실제 조치 전 반드시 관련 전문가·기관에 재확인하시기 바랍니다.
        </div>
      </div>
    </div>
  )
}
