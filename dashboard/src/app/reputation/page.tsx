'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { adminFetch } from '@/lib/adminAuth'

type Academy = {
  id: number
  external_id: string
  name: string
  region: string | null
  subjects: string | null
  academy_type: string | null
  target_grades: string | null
  edu_office_reg_no: string | null
  created_at: string
}

const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', border: '1px solid #D8D3C4', borderRadius: 4,
  padding: '8px 10px', fontSize: 13.5, fontFamily: 'inherit',
}
const labelStyle: React.CSSProperties = {
  fontSize: 12, fontWeight: 700, color: '#5B5342', display: 'block', marginBottom: 6,
}

function ReputationListContent() {
  const [academies, setAcademies] = useState<Academy[]>([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    name: '', region: '', subjects: '', academy_type: '', target_grades: '', edu_office_reg_no: '',
  })
  const [creating, setCreating] = useState(false)

  async function loadAcademies(query: string) {
    setLoading(true)
    setError('')
    try {
      const res = await adminFetch(`academies${query ? `?q=${encodeURIComponent(query)}` : ''}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `목록을 불러오지 못했습니다 (${res.status})`)
      setAcademies(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '목록을 불러오지 못했습니다')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAcademies('') }, [])

  async function createAcademy() {
    if (!form.name.trim() || creating) return
    setCreating(true)
    setError('')
    try {
      const res = await adminFetch('academies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          region: form.region || null,
          subjects: form.subjects || null,
          academy_type: form.academy_type || null,
          target_grades: form.target_grades || null,
          edu_office_reg_no: form.edu_office_reg_no || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `등록 실패 (${res.status})`)
      setForm({ name: '', region: '', subjects: '', academy_type: '', target_grades: '', edu_office_reg_no: '' })
      await loadAcademies(q)
    } catch (err) {
      setError(err instanceof Error ? err.message : '등록 중 오류가 발생했습니다')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div style={{
      fontFamily: "'Noto Sans KR', -apple-system, sans-serif",
      background: '#F1EFE8', minHeight: '100vh', padding: '32px 16px',
    }}>
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{
            fontFamily: 'ui-monospace, monospace', fontSize: 11.5, letterSpacing: 1.5,
            color: '#7c5cff', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6,
          }}>학원 평판 인텔리전스 · 내부용</div>
          <h1 style={{
            fontFamily: "Georgia, 'Noto Serif KR', serif", fontSize: 26, margin: 0,
            color: '#1D1B16', fontWeight: 700, letterSpacing: -0.3,
          }}>학원 등록 및 평판 관리</h1>
          <div style={{ fontSize: 13.5, color: '#6B6558', marginTop: 6 }}>
            학원을 등록하고 상세 페이지에서 설문·운영지표·평판 점수를 관리합니다.
          </div>
        </div>

        <div style={{ background: '#fff', border: '1px solid #E4E0D5', borderRadius: 6, padding: 18, marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#5B5342', marginBottom: 12 }}>새 학원 등록</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
            <div>
              <label style={labelStyle}>학원명 *</label>
              <input style={inputStyle} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="예: 강남영어학원" />
            </div>
            <div>
              <label style={labelStyle}>지역</label>
              <input style={inputStyle} value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} placeholder="예: 강남구" />
            </div>
            <div>
              <label style={labelStyle}>과목</label>
              <input style={inputStyle} value={form.subjects} onChange={(e) => setForm({ ...form, subjects: e.target.value })} placeholder="예: 영어,수학" />
            </div>
            <div>
              <label style={labelStyle}>학원 유형</label>
              <input style={inputStyle} value={form.academy_type} onChange={(e) => setForm({ ...form, academy_type: e.target.value })} placeholder="예: 종합" />
            </div>
            <div>
              <label style={labelStyle}>대상 학년</label>
              <input style={inputStyle} value={form.target_grades} onChange={(e) => setForm({ ...form, target_grades: e.target.value })} placeholder="예: 초등,중등" />
            </div>
            <div>
              <label style={labelStyle}>교육청 등록번호</label>
              <input style={inputStyle} value={form.edu_office_reg_no} onChange={(e) => setForm({ ...form, edu_office_reg_no: e.target.value })} />
            </div>
          </div>
          <button
            onClick={createAcademy}
            disabled={creating || !form.name.trim()}
            style={{
              background: creating ? '#B8B2A0' : '#1D1B16', color: '#fff', border: 'none',
              borderRadius: 4, padding: '9px 16px', fontSize: 13.5, fontWeight: 700,
              cursor: creating ? 'default' : 'pointer',
            }}
          >{creating ? '등록 중…' : '학원 등록'}</button>
          {error && <div style={{ color: '#8C2F26', fontSize: 13, marginTop: 8 }}>{error}</div>}
        </div>

        <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
          <input
            style={{ ...inputStyle, maxWidth: 280 }}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') loadAcademies(q) }}
            placeholder="학원명 검색"
          />
          <button
            onClick={() => loadAcademies(q)}
            style={{ background: '#fff', border: '1px solid #D8D3C4', borderRadius: 4, padding: '8px 14px', fontSize: 13, cursor: 'pointer' }}
          >검색</button>
        </div>

        <div style={{ background: '#fff', border: '1px solid #E4E0D5', borderRadius: 6, overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: 20, fontSize: 13, color: '#6B6558' }}>불러오는 중…</div>
          ) : academies.length === 0 ? (
            <div style={{ padding: 20, fontSize: 13, color: '#6B6558' }}>등록된 학원이 없습니다.</div>
          ) : (
            academies.map((a) => (
              <Link key={a.id} href={`/reputation/${a.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '14px 16px', borderBottom: '1px solid #EEEAE0', cursor: 'pointer',
                }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14.5, color: '#1D1B16' }}>{a.name}</div>
                    <div style={{ fontSize: 12, color: '#9A9384', fontFamily: 'ui-monospace, monospace', marginTop: 2 }}>{a.external_id}</div>
                  </div>
                  <div style={{ fontSize: 12.5, color: '#6B6558', textAlign: 'right' }}>
                    {a.region && <div>{a.region}</div>}
                    {a.subjects && <div>{a.subjects}</div>}
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default function ReputationListPage() {
  return <ReputationListContent />
}
