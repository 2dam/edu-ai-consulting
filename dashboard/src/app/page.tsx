'use client'
import dynamic from 'next/dynamic'
import { useState, useEffect, useCallback } from 'react'
import type { AcademyNode, GangnamAcademy, LayerId } from '@/lib/data'
import { LAYERS } from '@/lib/data'
import HUD from '@/components/HUD'

// MapLibre는 SSR 불가 — 클라이언트에서만 로드
const Map = dynamic(() => import('@/components/Map'), { ssr: false, loading: () => (
  <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0a0c10' }}>
    <div style={{ color: '#f97316', fontFamily: 'monospace' }}>EDUINTEL 초기화 중...</div>
  </div>
)})

export default function Page() {
  const [data, setData] = useState<{
    regions: AcademyNode[]
    gangnam_academies: GangnamAcademy[]
    backend_record_count: number
    loop_status: any
  } | null>(null)
  const [news, setNews] = useState<any[]>([])
  const [activeLayers, setActiveLayers] = useState<Set<LayerId>>(
    new Set(LAYERS.filter(l => l.default).map(l => l.id))
  )
  const [selected, setSelected] = useState<AcademyNode | GangnamAcademy | null>(null)

  useEffect(() => {
    fetch('/api/education').then(r => r.json()).then(setData).catch(console.error)
    fetch('/api/news').then(r => r.json()).then(d => setNews(d.items)).catch(console.error)
    // 30초마다 갱신
    const id = setInterval(() => {
      fetch('/api/education').then(r => r.json()).then(setData).catch(console.error)
    }, 30_000)
    return () => clearInterval(id)
  }, [])

  const toggleLayer = useCallback((id: LayerId) => {
    setActiveLayers(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  if (!data) {
    return (
      <div style={{ width: '100vw', height: '100vh', background: '#0a0c10', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
        <div style={{ width: 40, height: 40, border: '2px solid #f97316', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <div style={{ color: '#f97316', fontFamily: 'monospace', letterSpacing: '0.1em' }}>EDUINTEL LOADING</div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {/* 지도 전체화면 */}
      <div style={{ position: 'absolute', inset: 0 }}>
        <Map
          regions={data.regions}
          gangnamAcademies={data.gangnam_academies}
          activeLayers={activeLayers}
          onSelect={setSelected}
        />
      </div>

      {/* HUD 오버레이 */}
      <HUD
        regions={data.regions}
        loopStatus={data.loop_status}
        backendCount={data.backend_record_count}
        activeLayers={activeLayers}
        onToggleLayer={toggleLayer}
        selected={selected}
        news={news}
      />
    </div>
  )
}
