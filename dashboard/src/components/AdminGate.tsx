'use client'
import { useEffect, useState } from 'react'
import { getAdminToken, setAdminToken } from '@/lib/adminAuth'

async function checkToken(token: string): Promise<boolean> {
  const res = await fetch('/api/reputation/academies', { headers: { 'X-Admin-Token': token } })
  return res.ok
}

export default function AdminGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<'checking' | 'locked' | 'unlocked'>('checking')
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const existing = getAdminToken()
    if (!existing) {
      setStatus('locked')
      return
    }
    checkToken(existing).then((ok) => setStatus(ok ? 'unlocked' : 'locked'))
  }, [])

  async function submit() {
    if (!input.trim() || busy) return
    setBusy(true)
    setError('')
    try {
      const ok = await checkToken(input)
      if (ok) {
        setAdminToken(input)
        setStatus('unlocked')
      } else {
        setError('코드가 올바르지 않습니다')
      }
    } catch {
      setError('확인 중 오류가 발생했습니다')
    } finally {
      setBusy(false)
    }
  }

  if (status === 'checking') {
    return <div style={{ padding: 32, fontFamily: 'sans-serif', color: '#6B6558' }}>확인 중…</div>
  }

  if (status === 'unlocked') {
    return <>{children}</>
  }

  return (
    <div style={{
      fontFamily: "'Noto Sans KR', -apple-system, sans-serif", background: '#F1EFE8',
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div style={{ background: '#fff', border: '1px solid #E4E0D5', borderRadius: 8, padding: 28, maxWidth: 340, width: '100%' }}>
        <div style={{ fontSize: 12, color: '#7c5cff', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
          내부 컨설턴트 전용
        </div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#1D1B16', marginBottom: 14 }}>관리자 코드를 입력하세요</div>
        <input
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
          style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #D8D3C4', borderRadius: 4, padding: '9px 10px', fontSize: 14, marginBottom: 10 }}
          autoFocus
        />
        <button
          onClick={submit}
          disabled={busy || !input.trim()}
          style={{
            width: '100%', background: busy || !input.trim() ? '#B8B2A0' : '#1D1B16', color: '#fff', border: 'none',
            borderRadius: 4, padding: '10px 0', fontSize: 13.5, fontWeight: 700, cursor: busy ? 'default' : 'pointer',
          }}
        >{busy ? '확인 중…' : '확인'}</button>
        {error && <div style={{ color: '#8C2F26', fontSize: 12.5, marginTop: 8 }}>{error}</div>}
      </div>
    </div>
  )
}
