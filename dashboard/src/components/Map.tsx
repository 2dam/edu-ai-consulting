'use client'
import { useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from 'react'
import type { AcademyNode, GangnamAcademy, LayerId, CctvPoint, EducationFacility } from '@/lib/data'
import { KOREA_CENTER } from '@/lib/data'

export interface MapHandle {
  flyTo: (lat: number, lng: number, zoom: number) => void
}

interface MapProps {
  regions: AcademyNode[]
  gangnamAcademies: GangnamAcademy[]
  activeLayers: Set<LayerId>
  onSelect: (item: AcademyNode | GangnamAcademy | null) => void
  dropoutRisks?: Record<string, { risk_probability: number; predicted_label: string; top_factor: string | null }>
  universities?: Array<{ id: string; name: string; short: string; lat: number; lng: number; rank: number; cutoff_avg: number; region: string }>
  cctvPoints?: CctvPoint[]
  educationFacilities?: EducationFacility[]
}

const FACILITY_LABEL: Record<string, string> = { daycare: '어린이집', kindergarten: '유치원', elementary: '초등학교', academy: '학원', university: '대학' }

// 점수→색상 (낮음=파랑, 중간=노랑, 높음=빨강)
function gapColor(gap: number): string {
  if (gap > 0.8) return '#ef4444'
  if (gap > 0.6) return '#f97316'
  if (gap > 0.4) return '#eab308'
  return '#22c55e'
}

function tierColor(tier: 'S' | 'A' | 'B' | 'C'): string {
  return { S: '#f97316', A: '#eab308', B: '#3b82f6', C: '#64748b' }[tier]
}

const Map = forwardRef<MapHandle, MapProps>(function Map(
  { regions, gangnamAcademies, activeLayers, onSelect, dropoutRisks = {}, universities = [], cctvPoints = [], educationFacilities = [] },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const popupRef = useRef<any>(null)

  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, zoom) => {
      mapRef.current?.flyTo({ center: [lng, lat], zoom, duration: 1200 })
    },
  }))

  const addLayers = useCallback((map: any, maplibre: any) => {
    // ── 0. 중도탈락 위험도 레이어 ────────────────────────────────────────
    if (!map.getSource('dropout') && Object.keys(dropoutRisks).length > 0) {
      map.addSource('dropout', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: regions
            .filter(r => dropoutRisks[r.id])
            .map(r => ({
              type: 'Feature',
              geometry: { type: 'Point', coordinates: [r.lng, r.lat] },
              properties: {
                risk: dropoutRisks[r.id]?.risk_probability ?? 0,
                label: dropoutRisks[r.id]?.predicted_label ?? '',
                factor: dropoutRisks[r.id]?.top_factor ?? '',
                name: r.name,
              },
            })),
        },
      })
      map.addLayer({
        id: 'dropout-circles',
        type: 'circle',
        source: 'dropout',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'risk'], 0, 6, 1, 22],
          'circle-color': ['interpolate', ['linear'], ['get', 'risk'], 0, '#22c55e', 0.4, '#eab308', 0.7, '#f97316', 1, '#ef4444'],
          'circle-opacity': 0.7,
          'circle-stroke-width': 1,
          'circle-stroke-color': 'rgba(255,255,255,0.2)',
        },
        layout: { visibility: activeLayers.has('dropout-risk') ? 'visible' : 'none' },
      })
      map.on('click', 'dropout-circles', (e: any) => {
        const p = e.features[0].properties
        new maplibre.Popup({ closeButton: false })
          .setLngLat(e.lngLat)
          .setHTML(`<b>${p.name}</b><br>위험도: <b style="color:${p.risk > 0.5 ? '#ef4444' : '#22c55e'}">${(p.risk * 100).toFixed(0)}%</b><br>주요 요인: ${p.factor || '—'}`)
          .addTo(map)
      })
    }

    // ── 0b. 주요 대학 레이어 ─────────────────────────────────────────────
    if (!map.getSource('universities') && universities.length > 0) {
      map.addSource('universities', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: universities.map(u => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [u.lng, u.lat] },
            properties: { ...u },
          })),
        },
      })
      map.addLayer({
        id: 'university-circles',
        type: 'circle',
        source: 'universities',
        paint: {
          'circle-radius': 7,
          'circle-color': '#3b82f6',
          'circle-stroke-width': 2,
          'circle-stroke-color': '#93c5fd',
          'circle-opacity': 0.85,
        },
        layout: { visibility: activeLayers.has('universities') ? 'visible' : 'none' },
      })
      map.addLayer({
        id: 'university-labels',
        type: 'symbol',
        source: 'universities',
        layout: {
          'text-field': ['get', 'short'],
          'text-size': 9,
          'text-offset': [0, 1.6],
          'text-anchor': 'top',
          visibility: activeLayers.has('universities') ? 'visible' : 'none',
        },
        paint: { 'text-color': '#93c5fd', 'text-halo-color': '#0a0c10', 'text-halo-width': 1 },
      })
      map.on('click', 'university-circles', (e: any) => {
        const p = e.features[0].properties
        new maplibre.Popup({ closeButton: false })
          .setLngLat(e.lngLat)
          .setHTML(`<b>${p.name}</b><br>정시 커트라인 평균: <b style="color:#3b82f6">${p.cutoff_avg}점</b><br>전국 ${p.rank}위`)
          .addTo(map)
      })
    }
    // ── 1. 교육격차 히트맵 ───────────────────────────────────────────────
    if (!map.getSource('regions')) {
      map.addSource('regions', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: regions.map(r => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [r.lng, r.lat] },
            properties: { ...r },
          })),
        },
      })
    }

    if (!map.getLayer('gap-heatmap-layer')) {
      map.addLayer({
        id: 'gap-heatmap-layer',
        type: 'heatmap',
        source: 'regions',
        paint: {
          'heatmap-weight': ['/', ['get', 'gap_index'], 1],
          'heatmap-intensity': 1.2,
          'heatmap-radius': 60,
          'heatmap-color': [
            'interpolate', ['linear'], ['heatmap-density'],
            0, 'rgba(0,0,0,0)',
            0.3, '#3b82f6',
            0.6, '#eab308',
            1, '#ef4444',
          ],
          'heatmap-opacity': 0.55,
        },
        layout: { visibility: activeLayers.has('gap-heatmap') ? 'visible' : 'none' },
      })
    }

    // ── 2. 학원 밀도 원형 마커 ───────────────────────────────────────────
    if (!map.getLayer('academy-circles')) {
      map.addLayer({
        id: 'academy-circles',
        type: 'circle',
        source: 'regions',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'academy_count'], 200, 8, 4000, 28],
          'circle-color': ['case',
            ['==', ['get', 'tier'], 'S'], '#f97316',
            ['==', ['get', 'tier'], 'A'], '#eab308',
            ['==', ['get', 'tier'], 'B'], '#3b82f6',
            '#64748b'
          ],
          'circle-opacity': 0.75,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': 'rgba(255,255,255,0.3)',
        },
        layout: { visibility: activeLayers.has('academy-density') ? 'visible' : 'none' },
      })

      map.addLayer({
        id: 'academy-labels',
        type: 'symbol',
        source: 'regions',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 10,
          'text-offset': [0, 1.8],
          'text-anchor': 'top',
          visibility: activeLayers.has('academy-density') ? 'visible' : 'none',
        },
        paint: {
          'text-color': '#e2e8f0',
          'text-halo-color': '#0a0c10',
          'text-halo-width': 1,
        },
      })

      map.on('click', 'academy-circles', (e: any) => {
        const props = e.features[0].properties
        const node = regions.find(r => r.id === props.id)
        if (node) onSelect(node)
      })
      map.on('mouseenter', 'academy-circles', () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', 'academy-circles', () => { map.getCanvas().style.cursor = '' })
    }

    // ── 3. 강남 8학군 영역 ───────────────────────────────────────────────
    if (!map.getSource('gangnam-zone') && activeLayers.has('gangnam-zone')) {
      map.addSource('gangnam-zone', {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [[
              [127.020, 37.475], [127.085, 37.475],
              [127.085, 37.535], [127.020, 37.535],
              [127.020, 37.475],
            ]],
          },
          properties: {},
        },
      })
      map.addLayer({
        id: 'gangnam-zone-fill',
        type: 'fill',
        source: 'gangnam-zone',
        paint: { 'fill-color': '#eab308', 'fill-opacity': 0.06 },
      })
      map.addLayer({
        id: 'gangnam-zone-line',
        type: 'line',
        source: 'gangnam-zone',
        paint: { 'line-color': '#eab308', 'line-width': 1.5, 'line-dasharray': [4, 3] },
      })
    }

    // ── 4. 강남 학원 마커 ────────────────────────────────────────────────
    if (!map.getSource('gangnam-academies')) {
      map.addSource('gangnam-academies', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: gangnamAcademies.map(a => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [a.lng, a.lat] },
            properties: { ...a },
          })),
        },
      })
      map.addLayer({
        id: 'gangnam-academy-dots',
        type: 'circle',
        source: 'gangnam-academies',
        paint: {
          'circle-radius': 7,
          'circle-color': '#f97316',
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
          'circle-opacity': 0.9,
        },
        layout: { visibility: activeLayers.has('gangnam-zone') ? 'visible' : 'none' },
      })
      map.on('click', 'gangnam-academy-dots', (e: any) => {
        const props = e.features[0].properties
        const acad = gangnamAcademies.find(a => a.id === props.id)
        if (acad) onSelect(acad)
      })
    }

    // ── 5. 스캔 펄스 애니메이션 (강남 중심) ─────────────────────────────
    if (!map.getSource('pulse')) {
      map.addSource('pulse', {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'Point', coordinates: [127.0473, 37.5172] }, properties: {} },
      })
      map.addLayer({
        id: 'pulse-ring',
        type: 'circle',
        source: 'pulse',
        paint: {
          'circle-radius': 0,
          'circle-color': 'transparent',
          'circle-stroke-width': 2,
          'circle-stroke-color': '#f97316',
          'circle-stroke-opacity': 0,
        },
      })
      let r = 0
      const animate = () => {
        r = (r + 0.3) % 60
        map.setPaintProperty('pulse-ring', 'circle-radius', r)
        map.setPaintProperty('pulse-ring', 'circle-stroke-opacity', Math.max(0, 1 - r / 60))
        requestAnimationFrame(animate)
      }
      animate()
    }
  }, [regions, gangnamAcademies, activeLayers, onSelect])

  useEffect(() => {
    if (!containerRef.current) return
    let map: any

    import('maplibre-gl').then(({ default: maplibregl }) => {
      map = new maplibregl.Map({
        container: containerRef.current!,
        style: {
          version: 8,
          glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
          sources: {
            'carto-dark': {
              type: 'raster',
              tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'],
              tileSize: 256,
              attribution: '© CartoDB © OpenStreetMap',
            },
          },
          layers: [{ id: 'carto-dark', type: 'raster', source: 'carto-dark' }],
        },
        center: [KOREA_CENTER.lng, KOREA_CENTER.lat],
        zoom: KOREA_CENTER.zoom,
        antialias: true,
      })

      popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
      mapRef.current = map

      map.on('load', () => addLayers(map, maplibregl))
    })

    return () => { map?.remove() }
  }, [])

  // 레이어 가시성 토글
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const toggle = (id: string, visible: boolean) => {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
    }
    toggle('gap-heatmap-layer', activeLayers.has('gap-heatmap'))
    toggle('academy-circles', activeLayers.has('academy-density'))
    toggle('academy-labels', activeLayers.has('academy-density'))
    toggle('gangnam-academy-dots', activeLayers.has('gangnam-zone'))
    toggle('gangnam-zone-fill', activeLayers.has('gangnam-zone'))
    toggle('gangnam-zone-line', activeLayers.has('gangnam-zone'))
    toggle('dropout-circles', activeLayers.has('dropout-risk'))
    toggle('university-circles', activeLayers.has('universities'))
    toggle('university-labels', activeLayers.has('universities'))
    toggle('cctv-dots', activeLayers.has('cctv'))
    toggle('early-education-dots', activeLayers.has('early-education'))
  }, [activeLayers])

  // ── 전국 공공 CCTV / 어린이집·유치원·초등학교 (비동기 도착 데이터라 별도 동기화) ──
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const sync = () => {
      import('maplibre-gl').then((maplibre) => {
        // CCTV — ITS 공개 도로 구간 CCTV만 대상 (시설 내부 CCTV 아님)
        const cctvData = {
          type: 'FeatureCollection' as const,
          features: cctvPoints
            .filter(c => c.lat && c.lng)
            .map(c => ({
              type: 'Feature' as const,
              geometry: { type: 'Point' as const, coordinates: [c.lng, c.lat] },
              properties: { ...c },
            })),
        }
        const cctvSource: any = map.getSource('cctv')
        if (cctvSource) {
          cctvSource.setData(cctvData)
        } else {
          map.addSource('cctv', { type: 'geojson', data: cctvData })
          map.addLayer({
            id: 'cctv-dots',
            type: 'circle',
            source: 'cctv',
            paint: {
              'circle-radius': 5,
              'circle-color': '#14b8a6',
              'circle-stroke-width': 1.5,
              'circle-stroke-color': '#fff',
              'circle-opacity': 0.85,
            },
            layout: { visibility: activeLayers.has('cctv') ? 'visible' : 'none' },
          })
          map.on('click', 'cctv-dots', (e: any) => {
            const p = e.features[0].properties
            new maplibre.Popup({ closeButton: false })
              .setLngLat(e.lngLat)
              .setHTML(
                `<b>${p.name}</b><br>형식: ${p.format || '—'}<br>` +
                `<a href="${p.stream_url}" target="_blank" rel="noreferrer" style="color:#14b8a6">실시간 영상 열기 →</a>`
              )
              .addTo(map)
          })
          map.on('mouseenter', 'cctv-dots', () => { map.getCanvas().style.cursor = 'pointer' })
          map.on('mouseleave', 'cctv-dots', () => { map.getCanvas().style.cursor = '' })
        }

        // 어린이집·유치원·초등학교 (주소 지오코딩 전까지는 좌표가 있는 항목만 표시)
        const eduData = {
          type: 'FeatureCollection' as const,
          features: educationFacilities
            .filter(f => f.data.lat && f.data.lng)
            .map(f => ({
              type: 'Feature' as const,
              geometry: { type: 'Point' as const, coordinates: [f.data.lng!, f.data.lat!] },
              properties: {
                id: f.id,
                name: f.data.name,
                facility_type: f.data.facility_type,
                region: f.data.region,
                address: f.data.address,
                evaluation_grade: f.data.evaluation_grade || '',
                status_note: f.data.status_note || '',
              },
            })),
        }
        const eduSource: any = map.getSource('early-education')
        if (eduSource) {
          eduSource.setData(eduData)
        } else {
          map.addSource('early-education', { type: 'geojson', data: eduData })
          map.addLayer({
            id: 'early-education-dots',
            type: 'circle',
            source: 'early-education',
            paint: {
              'circle-radius': 5,
              'circle-color': [
                'match', ['get', 'facility_type'],
                'daycare', '#ec4899',
                'kindergarten', '#f472b6',
                'elementary', '#db2777',
                'academy', '#a21caf',
                'university', '#3b82f6',
                '#ec4899',
              ],
              'circle-stroke-width': 1.5,
              'circle-stroke-color': '#fff',
              'circle-opacity': 0.85,
            },
            layout: { visibility: activeLayers.has('early-education') ? 'visible' : 'none' },
          })
          map.on('click', 'early-education-dots', (e: any) => {
            const p = e.features[0].properties
            const label = FACILITY_LABEL[p.facility_type] || p.facility_type
            const gradeLine = p.evaluation_grade ? `<br>평가등급: <b>${p.evaluation_grade}</b>` : ''
            const statusLine = p.status_note ? `<br>등록상태: ${p.status_note}` : ''
            new maplibre.Popup({ closeButton: false })
              .setLngLat(e.lngLat)
              .setHTML(`<b>${p.name}</b><br>${label} · ${p.region || ''}<br>${p.address || ''}${gradeLine}${statusLine}`)
              .addTo(map)
          })
          map.on('mouseenter', 'early-education-dots', () => { map.getCanvas().style.cursor = 'pointer' })
          map.on('mouseleave', 'early-education-dots', () => { map.getCanvas().style.cursor = '' })
        }
      })
    }

    if (map.isStyleLoaded()) sync()
    else map.once('load', sync)
  }, [cctvPoints, educationFacilities, activeLayers])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
})

export default Map
