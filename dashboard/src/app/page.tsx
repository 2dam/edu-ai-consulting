'use client'
import dynamic from 'next/dynamic'
import { useState, useEffect, useCallback, useRef } from 'react'
import type { AcademyNode, GangnamAcademy, LayerId, CctvPoint, EducationFacility } from '@/lib/data'
import { LAYERS } from '@/lib/data'
import HUD from '@/components/HUD'
import OsintPanel from '@/components/OsintPanel'
import type { MapHandle } from '@/components/Map'

const Map = dynamic(
  () => import('@/components/Map').then(m => ({ default: m.default })),
  {
    ssr: false,
    loading: () => (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0a0c10' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 40, height: 40, border: '2px solid #f97316', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
          <div style={{ color: '#f97316', fontFamily: 'monospace', letterSpacing: '0.1em', fontSize: 12 }}>EDUINTEL 초기화 중...</div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    ),
  }
) as any

export default function Page() {
  const mapRef = useRef<MapHandle>(null)

  const [data, setData] = useState<{
    regions: AcademyNode[]
    gangnam_academies: GangnamAcademy[]
    backend_record_count: number
    loop_status: any
  } | null>(null)
  const [news, setNews] = useState<any[]>([])
  const [dropoutRisks, setDropoutRisks] = useState<Record<string, any>>({})
  const [universities, setUniversities] = useState<any[]>([])
  const [cctvPoints, setCctvPoints] = useState<CctvPoint[]>([])
  const [educationFacilities, setEducationFacilities] = useState<EducationFacility[]>([])
  const [activeLayers, setActiveLayers] = useState<Set<LayerId>>(
    new Set(LAYERS.filter(l => l.default).map(l => l.id))
  )
  const [selected, setSelected] = useState<AcademyNode | GangnamAcademy | null>(null)

  useEffect(() => {
    const load = () => fetch('/api/education').then(r => r.json()).then(setData).catch(console.error)
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    fetch('/api/news').then(r => r.json()).then(d => setNews(d.items)).catch(console.error)
    fetch('/api/dropout').then(r => r.json()).then(d => setDropoutRisks(d.dropout_risks)).catch(console.error)
    fetch('/api/universities').then(r => r.json()).then(d => setUniversities(d.universities)).catch(console.error)
    fetch('/api/cctv').then(r => r.json()).then(d => setCctvPoints(d.items)).catch(console.error)
    fetch('/api/education-facilities').then(r => r.json()).then(d => setEducationFacilities(d.items)).catch(console.error)
  }, [])

  const toggleLayer = useCallback((id: LayerId) => {
    setActiveLayers(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  const flyTo = useCallback((lat: number, lng: number, zoom: number) => {
    mapRef.current?.flyTo(lat, lng, zoom)
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
          ref={mapRef}
          regions={data.regions}
          gangnamAcademies={data.gangnam_academies}
          activeLayers={activeLayers}
          onSelect={setSelected}
          dropoutRisks={dropoutRisks}
          universities={universities}
          cctvPoints={cctvPoints}
          educationFacilities={educationFacilities}
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

      {/* OSINT 분석 패널 */}
      <OsintPanel
        regions={data.regions}
        onFlyTo={flyTo}
        educationFacilities={educationFacilities}
      />
    </div>
  )
}
