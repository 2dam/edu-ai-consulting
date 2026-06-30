'use client'
import { useEffect, useRef, useCallback } from 'react'
import type { AcademyNode, GangnamAcademy, LayerId } from '@/lib/data'
import { KOREA_CENTER } from '@/lib/data'

interface MapProps {
  regions: AcademyNode[]
  gangnamAcademies: GangnamAcademy[]
  activeLayers: Set<LayerId>
  onSelect: (item: AcademyNode | GangnamAcademy | null) => void
}

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

export default function Map({ regions, gangnamAcademies, activeLayers, onSelect }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const popupRef = useRef<any>(null)

  const addLayers = useCallback((map: any, maplibre: any) => {
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
  }, [activeLayers])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
