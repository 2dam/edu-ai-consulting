'use client'
import dynamic from 'next/dynamic'
import { useState, useEffect, useCallback, useRef } from 'react'
import type { AcademyNode, LayerId, CctvPoint, EducationFacility } from '@/lib/data'
import { LAYERS, SAMPLE_EDUCATION_FACILITIES } from '@/lib/data'
import HUD from '@/components/HUD'
import OsintPanel from '@/components/OsintPanel'
import VideoPanel from '@/components/VideoPanel'
import ParentsPortalPanel from '@/components/ParentsPortalPanel'
import ConsultingIntelPanel from '@/components/ConsultingIntelPanel'
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

// 백엔드 콜드스타트 등으로 첫 응답이 비어있을 때 몇 초 간격으로 재시도한다.
// onData가 true를 반환하면(사용할 만한 데이터를 받으면) 멈추고, false면 다음 시도를 예약한다.
function pollUntilReady(url: string, onData: (data: any) => boolean, maxAttempts = 4, delayMs = 4000) {
  let attempt = 0
  const tick = () => {
    attempt++
    fetch(url)
      .then(r => r.json())
      .then(d => {
        const done = onData(d)
        if (!done && attempt < maxAttempts) setTimeout(tick, delayMs)
      })
      .catch(() => {
        if (attempt < maxAttempts) setTimeout(tick, delayMs)
      })
  }
  tick()
}

export default function Page() {
  const mapRef = useRef<MapHandle>(null)

  const [data, setData] = useState<{
    regions: AcademyNode[]
    backend_region_count: number
    loop_status: any
  } | null>(null)
  const [news, setNews] = useState<any[]>([])
  const [dropoutRisks, setDropoutRisks] = useState<Record<string, any>>({})
  const [universities, setUniversities] = useState<any[]>([])
  const [cctvPoints, setCctvPoints] = useState<CctvPoint[]>([])
  // 크롤러를 아직 안 돌렸어도 화면이 비어 보이지 않도록 예시 데이터로 시작 —
  // 실제 수집 데이터가 도착하면 아래 useEffect에서 자동으로 대체된다.
  const [educationFacilities, setEducationFacilities] = useState<EducationFacility[]>(SAMPLE_EDUCATION_FACILITIES)
  const [activeLayers, setActiveLayers] = useState<Set<LayerId>>(
    new Set(LAYERS.filter(l => l.default).map(l => l.id))
  )
  const [selected, setSelected] = useState<AcademyNode | null>(null)
  const [facilityPanelSignal, setFacilityPanelSignal] = useState(0)
  const [osintCommandSignal, setOsintCommandSignal] = useState<{
    seq: number
    tool: 'search' | 'gap-calc' | 'report' | 'facility-rating'
    regionId?: string
    facilityType?: EducationFacility['data']['facility_type'] | '전체'
    query?: string
  } | undefined>()

  useEffect(() => {
    const load = () => fetch('/api/education').then(r => r.json()).then(setData).catch(console.error)
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    // Render 무료/스타터 플랜은 트래픽이 없으면 백엔드가 슬립 상태로 들어가서,
    // 페이지 로드 시점의 첫 요청이 콜드스타트(15~30초+)에 걸려 실패하는 경우가 있다.
    // 아래 두 요청(뉴스·시설 평가정보)은 원래 1회성이라 그 순간 실패하면 새로고침 전까지
    // 계속 빈 상태/예시 데이터로 남는다 — 응답이 비어있으면 몇 초 간격으로 재시도한다.
    pollUntilReady('/api/news', (d) => {
      const items = d.items || []
      setNews(items)
      return items.length > 0
    })
    fetch('/api/dropout').then(r => r.json()).then(d => setDropoutRisks(d.dropout_risks)).catch(console.error)
    fetch('/api/universities').then(r => r.json()).then(d => setUniversities(d.universities)).catch(console.error)
    fetch('/api/cctv').then(r => r.json()).then(d => setCctvPoints(d.items)).catch(console.error)
    pollUntilReady('/api/education-facilities', (d) => {
      const items = d.items || []
      // 실제 수집 데이터가 있을 때만 예시 데이터를 대체한다.
      if (items.length > 0) { setEducationFacilities(items); return true }
      return false
    })
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
          activeLayers={activeLayers}
          onSelect={setSelected}
          dropoutRisks={dropoutRisks}
          universities={universities}
          cctvPoints={cctvPoints}
          educationFacilities={educationFacilities}
        />
      </div>

      {/* HUD 오버레이 — 학부모On누리 패널은 좌측 flex column(시스템 현황과 데이터
          레이어 사이)에 자연스럽게 쌓이도록 leftPanelExtra로 전달한다. */}
      <HUD
        regions={data.regions}
        loopStatus={data.loop_status}
        backendCount={data.backend_region_count}
        activeLayers={activeLayers}
        onToggleLayer={toggleLayer}
        selected={selected}
        news={news}
        onOpenFacilityPanel={() => setFacilityPanelSignal(n => n + 1)}
        cctvCount={cctvPoints.length}
        leftPanelExtra={<ParentsPortalPanel />}
        rightPanelExtra={
          <ConsultingIntelPanel
            regions={data.regions}
            facilities={educationFacilities}
            onOpenOsint={command => setOsintCommandSignal({
              seq: Date.now(),
              ...command,
            })}
          />
        }
      />

      {/* OSINT 분석 패널 */}
      <OsintPanel
        regions={data.regions}
        onFlyTo={flyTo}
        educationFacilities={educationFacilities}
        openFacilityPanelSignal={facilityPanelSignal}
        openCommandSignal={osintCommandSignal}
      />

      {/* 실시간 교육 동영상 패널 */}
      <VideoPanel />
    </div>
  )
}
