'use client'
import { useEffect, useState, useRef } from 'react'
import AdminGate from '@/components/AdminGate'
import { adminFetch } from '@/lib/adminAuth'

type Academy = {
  id: number; external_id: string; name: string; region: string | null
  subjects: string | null; academy_type: string | null
}
type Score = {
  id: number; computed_at: string; overall_score: number
  category_scores: Record<string, number>; confidence_score: number
  sample_size: number; ai_summary: string | null
}
type Dashboard = { academy: Academy; latest_score: Score | null; score_history: Score[]; top_comments: string[] }
type Source = { id: number; source_type: string; url: string; created_at: string }
type Metric = {
  month: string; total_students: number | null; new_enrollments: number | null
  withdrawals: number | null; renewal_eligible: number | null; renewal_actual: number | null
  consultation_count: number | null; conversion_count: number | null
  attendance_rate: number | null; homework_rate: number | null
}
type Mention = {
  id: number; platform: string; source_url: string; post_title: string | null
  post_body: string | null; sentiment_label: 'positive' | 'neutral' | 'negative'; sentiment_score: number
}
type BenchmarkGroup = { available: boolean; label: string | null; average: number | null; sample_size: number | null; reason: string | null }
type Benchmark = {
  available: boolean; reason: string | null; our_score: number | null
  region: BenchmarkGroup | null; subject: BenchmarkGroup | null; size_tier: BenchmarkGroup | null; top20pct: BenchmarkGroup | null
}
type Forecast = {
  available: boolean; reason: string | null; current_score: number | null; projected_score: number | null
  projected_date: string | null; trend_direction: string | null
  key_driver: { category: string; delta: number } | null; at_risk_student_estimate: number | null
}

const SENTIMENT_STYLE: Record<Mention['sentiment_label'], { bg: string; fg: string; label: string }> = {
  positive: { bg: '#3E635518', fg: '#3E6355', label: '긍정' },
  neutral: { bg: '#9A938418', fg: '#6B6558', label: '중립' },
  negative: { bg: '#8C2F2618', fg: '#8C2F26', label: '부정' },
}

const card: React.CSSProperties = { background: '#fff', border: '1px solid #E4E0D5', borderRadius: 6, padding: 18, marginBottom: 20 }
const sectionTitle: React.CSSProperties = { fontSize: 13, fontWeight: 700, color: '#5B5342', marginBottom: 12 }
const btn = (disabled: boolean): React.CSSProperties => ({
  background: disabled ? '#B8B2A0' : '#1D1B16', color: '#fff', border: 'none',
  borderRadius: 4, padding: '9px 16px', fontSize: 13.5, fontWeight: 700,
  cursor: disabled ? 'default' : 'pointer',
})
const inputStyle: React.CSSProperties = {
  border: '1px solid #D8D3C4', borderRadius: 4, padding: '8px 10px', fontSize: 13.5, fontFamily: 'inherit',
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: '#5B5342', marginBottom: 4 }}>
        <span>{label}</span><span style={{ fontWeight: 700 }}>{value.toFixed(1)}</span>
      </div>
      <div style={{ background: '#F1EFE8', borderRadius: 3, height: 8, overflow: 'hidden' }}>
        <div style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: '#7c5cff', height: '100%' }} />
      </div>
    </div>
  )
}

function ReputationDashboardContent({ academyId }: { academyId: string }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [metrics, setMetrics] = useState<Metric[]>([])
  const [mentions, setMentions] = useState<Mention[]>([])
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null)
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [syncResult, setSyncResult] = useState('')

  const [newSourceUrl, setNewSourceUrl] = useState('')
  const [surveyUrl, setSurveyUrl] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadResult, setUploadResult] = useState('')

  async function loadAll() {
    setLoading(true)
    setError('')
    try {
      const [dRes, sRes, mRes, mentionRes, benchRes, forecastRes] = await Promise.all([
        adminFetch(`academies/${academyId}/dashboard`),
        adminFetch(`academies/${academyId}/sources`),
        adminFetch(`academies/${academyId}/metrics`),
        adminFetch(`academies/${academyId}/mentions`),
        adminFetch(`academies/${academyId}/benchmark`),
        adminFetch(`academies/${academyId}/forecast`),
      ])
      const d = await dRes.json()
      if (!dRes.ok) throw new Error(d?.detail || '학원 정보를 불러오지 못했습니다')
      setDashboard(d)
      setSources(sRes.ok ? await sRes.json() : [])
      setMetrics(mRes.ok ? await mRes.json() : [])
      setMentions(mentionRes.ok ? await mentionRes.json() : [])
      setBenchmark(benchRes.ok ? await benchRes.json() : null)
      setForecast(forecastRes.ok ? await forecastRes.json() : null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '불러오는 중 오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [academyId])

  async function addSource() {
    if (!newSourceUrl.trim() || busy) return
    setBusy(true)
    try {
      const res = await adminFetch(`academies/${academyId}/sources`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_type: 'other', url: newSourceUrl }),
      })
      if (!res.ok) throw new Error((await res.json())?.detail || '소스 등록 실패')
      setNewSourceUrl('')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : '소스 등록 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  async function createSurvey() {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const res = await adminFetch(`academies/${academyId}/surveys`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || '설문 생성 실패')
      setSurveyUrl(`${window.location.origin}${data.survey_url}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '설문 생성 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  async function uploadCsv() {
    const file = fileRef.current?.files?.[0]
    if (!file || busy) return
    setBusy(true)
    setUploadResult('')
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await adminFetch(`academies/${academyId}/metrics/upload`, { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || 'CSV 업로드 실패')
      setUploadResult(`가져옴 ${data.imported}건 · 갱신 ${data.updated}건${data.errors.length ? ` · 오류 ${data.errors.length}건` : ''}`)
      if (fileRef.current) fileRef.current.value = ''
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CSV 업로드 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  async function computeScore() {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const res = await adminFetch(`academies/${academyId}/score/compute`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || '점수 계산 실패')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : '점수 계산 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  async function syncMentions() {
    if (busy) return
    setBusy(true)
    setError('')
    setSyncResult('')
    try {
      const res = await adminFetch(`academies/${academyId}/mentions/sync`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || '동기화 실패')
      setSyncResult(`신규 ${data.synced}건 반영`)
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : '동기화 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  async function downloadPdf() {
    const res = await adminFetch(`academies/${academyId}/report.pdf`)
    if (!res.ok) {
      setError('PDF 다운로드 실패 — 먼저 평판 점수를 계산해주세요')
      return
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${dashboard?.academy.external_id || 'academy'}-reputation.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return <div style={{ padding: 32, fontFamily: 'sans-serif', color: '#6B6558' }}>불러오는 중…</div>
  }
  if (!dashboard) {
    return <div style={{ padding: 32, fontFamily: 'sans-serif', color: '#8C2F26' }}>{error || '학원을 찾을 수 없습니다'}</div>
  }

  const { academy, latest_score, score_history, top_comments } = dashboard

  return (
    <div style={{ fontFamily: "'Noto Sans KR', -apple-system, sans-serif", background: '#F1EFE8', minHeight: '100vh', padding: '32px 16px' }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: 11.5, letterSpacing: 1.5, color: '#7c5cff', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>
            {academy.external_id}
          </div>
          <h1 style={{ fontFamily: "Georgia, 'Noto Serif KR', serif", fontSize: 26, margin: 0, color: '#1D1B16', fontWeight: 700 }}>
            {academy.name}
          </h1>
          <div style={{ fontSize: 13.5, color: '#6B6558', marginTop: 6 }}>
            {[academy.region, academy.subjects, academy.academy_type].filter(Boolean).join(' · ') || '추가 정보 없음'}
          </div>
        </div>

        {error && <div style={{ color: '#8C2F26', fontSize: 13, marginBottom: 16 }}>{error}</div>}

        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={sectionTitle}>평판 점수</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={computeScore} disabled={busy} style={btn(busy)}>{busy ? '계산 중…' : '점수 계산'}</button>
              <button onClick={downloadPdf} disabled={!latest_score} style={{ ...btn(!latest_score), background: !latest_score ? '#B8B2A0' : '#5B5342' }}>PDF 다운로드</button>
            </div>
          </div>

          {latest_score ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginBottom: 14 }}>
                <div style={{ fontSize: 40, fontWeight: 700, color: '#1D1B16', fontFamily: "Georgia, serif" }}>
                  {latest_score.overall_score.toFixed(1)}
                </div>
                <div style={{ fontSize: 12.5, color: '#6B6558' }}>
                  데이터 신뢰도 <b>{latest_score.confidence_score.toFixed(0)}</b> · 표본 {latest_score.sample_size}건 ·
                  계산일 {new Date(latest_score.computed_at).toLocaleDateString('ko-KR')}
                </div>
              </div>
              {Object.entries(latest_score.category_scores).map(([k, v]) => <ScoreBar key={k} label={k} value={v} />)}

              {latest_score.ai_summary && (
                <div style={{ marginTop: 14, padding: 14, background: '#FBFAF7', border: '1px dashed #D8D3C4', borderRadius: 4, fontSize: 13.5, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                  {latest_score.ai_summary}
                </div>
              )}
              {!latest_score.ai_summary && (
                <div style={{ marginTop: 14, fontSize: 12.5, color: '#9A9384' }}>AI 요약 없음 (ANTHROPIC_API_KEY 미설정 또는 API 오류)</div>
              )}
            </>
          ) : (
            <div style={{ fontSize: 13, color: '#6B6558' }}>아직 계산된 점수가 없습니다. 설문 응답과 CSV 지표를 등록한 뒤 "점수 계산"을 눌러주세요.</div>
          )}

          {score_history.length > 1 && (
            <div style={{ marginTop: 18, borderTop: '1px dashed #D8D3C4', paddingTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#5B5342', marginBottom: 8 }}>이력</div>
              {score_history.map((s) => (
                <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: '#6B6558', padding: '4px 0' }}>
                  <span>{new Date(s.computed_at).toLocaleDateString('ko-KR')}</span>
                  <span>{s.overall_score.toFixed(1)}점 (신뢰도 {s.confidence_score.toFixed(0)})</span>
                </div>
              ))}
            </div>
          )}

          {top_comments.length > 0 && (
            <div style={{ marginTop: 18, borderTop: '1px dashed #D8D3C4', paddingTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#5B5342', marginBottom: 8 }}>최근 자유의견</div>
              {top_comments.map((c, i) => (
                <div key={i} style={{ fontSize: 13, color: '#2A2720', padding: '4px 0' }}>&ldquo;{c}&rdquo;</div>
              ))}
            </div>
          )}
        </div>

        <div style={card}>
          <div style={sectionTitle}>학부모·학생 설문</div>
          <button onClick={createSurvey} disabled={busy} style={btn(busy)}>설문 캠페인 생성 (QR/링크)</button>
          {surveyUrl && (
            <div style={{ marginTop: 12, padding: 10, background: '#F1EFE8', borderRadius: 4, fontSize: 13, fontFamily: 'ui-monospace, monospace', wordBreak: 'break-all' }}>
              {surveyUrl}
            </div>
          )}
        </div>

        <div style={card}>
          <div style={sectionTitle}>월간 운영 지표 (CSV 업로드)</div>
          <div style={{ fontSize: 12, color: '#9A9384', marginBottom: 10 }}>
            헤더: month,total_students,new_enrollments,withdrawals,renewal_eligible,renewal_actual,consultation_count,conversion_count,attendance_rate,homework_rate
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input ref={fileRef} type="file" accept=".csv" />
            <button onClick={uploadCsv} disabled={busy} style={btn(busy)}>업로드</button>
          </div>
          {uploadResult && <div style={{ marginTop: 8, fontSize: 12.5, color: '#3E6355' }}>{uploadResult}</div>}

          {metrics.length > 0 && (
            <table style={{ width: '100%', marginTop: 14, borderCollapse: 'collapse', fontSize: 12.5 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#5B5342' }}>
                  <th style={{ padding: '6px 4px' }}>월</th>
                  <th style={{ padding: '6px 4px' }}>재원생</th>
                  <th style={{ padding: '6px 4px' }}>재등록</th>
                  <th style={{ padding: '6px 4px' }}>출결률</th>
                  <th style={{ padding: '6px 4px' }}>숙제제출률</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={m.month} style={{ borderTop: '1px solid #EEEAE0' }}>
                    <td style={{ padding: '6px 4px' }}>{m.month}</td>
                    <td style={{ padding: '6px 4px' }}>{m.total_students ?? '-'}</td>
                    <td style={{ padding: '6px 4px' }}>{m.renewal_eligible ? `${m.renewal_actual}/${m.renewal_eligible}` : '-'}</td>
                    <td style={{ padding: '6px 4px' }}>{m.attendance_rate ?? '-'}</td>
                    <td style={{ padding: '6px 4px' }}>{m.homework_rate ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div style={card}>
          <div style={sectionTitle}>공개 소스 URL</div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            <input style={{ ...inputStyle, flex: 1 }} value={newSourceUrl} onChange={(e) => setNewSourceUrl(e.target.value)} placeholder="https://blog.naver.com/..." />
            <button onClick={addSource} disabled={busy || !newSourceUrl.trim()} style={btn(busy || !newSourceUrl.trim())}>추가</button>
          </div>
          {sources.length === 0 ? (
            <div style={{ fontSize: 13, color: '#9A9384' }}>등록된 소스가 없습니다.</div>
          ) : (
            sources.map((s) => (
              <div key={s.id} style={{ fontSize: 13, padding: '4px 0', color: '#2A2720', wordBreak: 'break-all' }}>{s.url}</div>
            ))
          )}
        </div>

        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={sectionTitle}>SNS 언급 (온라인평판)</div>
            <button onClick={syncMentions} disabled={busy} style={btn(busy)}>{busy ? '동기화 중…' : '동기화'}</button>
          </div>
          <div style={{ fontSize: 12, color: '#9A9384', marginBottom: 10 }}>
            실제 SNS 수집은 로컬에서 <code style={{ fontFamily: 'ui-monospace, monospace' }}>python academy_reputation_crawl.py --academy-id {academyId}</code> 를
            실행해야 합니다(운영자 전용, API 서버에는 크롤러가 포함되어 있지 않습니다). 이미 수집된 데이터를 여기서 동기화·감성분석합니다.
          </div>
          {syncResult && <div style={{ fontSize: 12.5, color: '#3E6355', marginBottom: 10 }}>{syncResult}</div>}
          {mentions.length === 0 ? (
            <div style={{ fontSize: 13, color: '#9A9384' }}>동기화된 언급이 없습니다.</div>
          ) : (
            mentions.map((m) => {
              const s = SENTIMENT_STYLE[m.sentiment_label]
              return (
                <div key={m.id} style={{ padding: '10px 0', borderTop: '1px solid #EEEAE0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 7px', borderRadius: 3, background: s.bg, color: s.fg }}>{s.label}</span>
                    <span style={{ fontSize: 11.5, color: '#9A9384' }}>{m.platform}</span>
                    <span style={{ fontWeight: 700, fontSize: 13.5, color: '#1D1B16' }}>{m.post_title}</span>
                  </div>
                  <div style={{ fontSize: 12.5, color: '#6B6558' }}>{(m.post_body || '').slice(0, 120)}</div>
                </div>
              )
            })
          )}
        </div>

        <div style={card}>
          <div style={sectionTitle}>경쟁 학원 비교 (익명 집계)</div>
          {!benchmark || !benchmark.available ? (
            <div style={{ fontSize: 13, color: '#6B6558' }}>{benchmark?.reason || '먼저 평판 점수를 계산해주세요'}</div>
          ) : (
            <>
              <div style={{ fontSize: 12.5, color: '#6B6558', marginBottom: 12 }}>
                우리 학원 <b style={{ color: '#1D1B16' }}>{benchmark.our_score?.toFixed(1)}점</b>
              </div>
              {[
                { key: 'region', title: `지역 평균 (${benchmark.region?.label || '-'})`, group: benchmark.region },
                { key: 'subject', title: '동일 과목 평균', group: benchmark.subject },
                { key: 'size_tier', title: `동일 규모 평균 (${benchmark.size_tier?.label || '-'})`, group: benchmark.size_tier },
                { key: 'top20pct', title: '상위 20% 평균', group: benchmark.top20pct },
              ].map(({ key, title, group }) => (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, padding: '5px 0', borderTop: '1px solid #EEEAE0' }}>
                  <span style={{ color: '#5B5342' }}>{title}</span>
                  {group?.available ? (
                    <span style={{ color: '#2A2720' }}>{group.average?.toFixed(1)}점 (표본 {group.sample_size}곳)</span>
                  ) : (
                    <span style={{ color: '#9A9384' }}>{group?.reason || '비교 불가'}</span>
                  )}
                </div>
              ))}
            </>
          )}
        </div>

        <div style={card}>
          <div style={sectionTitle}>평판 예측</div>
          {!forecast || !forecast.available ? (
            <div style={{ fontSize: 13, color: '#6B6558' }}>{forecast?.reason || '데이터가 부족합니다'}</div>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 13, color: '#6B6558' }}>현재 {forecast.current_score?.toFixed(1)}점</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#1D1B16' }}>→ {forecast.projected_score?.toFixed(1)}점</span>
                <span style={{
                  fontSize: 11.5, fontWeight: 700, padding: '2px 8px', borderRadius: 3,
                  background: forecast.trend_direction === '상승' ? '#3E635518' : forecast.trend_direction === '하락' ? '#8C2F2618' : '#9A938418',
                  color: forecast.trend_direction === '상승' ? '#3E6355' : forecast.trend_direction === '하락' ? '#8C2F26' : '#6B6558',
                }}>{forecast.trend_direction}</span>
              </div>
              <div style={{ fontSize: 12.5, color: '#6B6558', marginBottom: 6 }}>예측 기준일: {forecast.projected_date}</div>
              {forecast.key_driver && (
                <div style={{ fontSize: 12.5, color: '#6B6558', marginBottom: 6 }}>
                  주요 변동 요인: <b style={{ color: '#1D1B16' }}>{forecast.key_driver.category}</b> ({forecast.key_driver.delta > 0 ? '+' : ''}{forecast.key_driver.delta})
                </div>
              )}
              {forecast.at_risk_student_estimate !== null && (
                <div style={{ fontSize: 12.5, color: '#6B6558' }}>
                  추세 지속 시 예상 이탈 학생 수: <b style={{ color: '#1D1B16' }}>{forecast.at_risk_student_estimate}명</b>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ReputationDashboardClient({ academyId }: { academyId: string }) {
  return (
    <AdminGate>
      <ReputationDashboardContent academyId={academyId} />
    </AdminGate>
  )
}
