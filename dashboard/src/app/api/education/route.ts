import { NextResponse } from 'next/server'
import { REGION_NODES } from '@/lib/data'
import { BACKEND_URL } from '@/lib/backend'

export const dynamic = 'force-dynamic'

const BACKEND_TIMEOUT_MS = 20000
const BACKEND_CANDIDATES = Array.from(new Set([BACKEND_URL, 'https://ichapterwise.com'].filter(Boolean)))

// 나이스 학원교습소정보의 region은 전체 시도명("서울특별시")이거나 REGION_NODES가 쓰는
// 축약형("서울")과 다르게 표기되는 경우가 있어(예: "전남광주통합특별시(광주)") 접미사를
// 제거하고 부분 포함 매칭한다.
function normalizeRegionName(name: string): string {
  return name.replace(/(특별자치시|특별자치도|광역시|특별시|자치도|[시도])$/u, '')
}

interface RegionStatDistrict {
  region: string
  district: string
  academy_count: number
  gap_index: number
}

type BackendFetch<T> = { data: T; baseUrl: string }

async function fetchFromBackend<T>(path: string): Promise<BackendFetch<T> | null> {
  for (const baseUrl of BACKEND_CANDIDATES) {
    try {
      const res = await fetch(`${baseUrl}${path}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
      })
      if (!res.ok) {
        console.error(`backend ${path} responded`, baseUrl, res.status)
        continue
      }
      return { data: await res.json() as T, baseUrl }
    } catch (err) {
      console.error(`backend ${path} failed`, baseUrl, err)
    }
  }
  return null
}

// REGION_NODES 20개 중 광역시/특별자치시급 노드(이름 자체가 그 시 전체를 가리킴)는
// district 단위가 아니라 region 전체를 합산해야 한다 — 나머지(자치구, 도내 개별 시)는
// district 문자열 정확히 일치로 매칭한다.
const METRO_NODE_IDS = new Set([
  'busan', 'daegu', 'incheon', 'gwangju', 'daejeon', 'ulsan', 'sejong',
])

const METRO_REGION_NAME: Record<string, string> = {
  busan: '부산광역시',
  daegu: '대구광역시',
  incheon: '인천광역시',
  gwangju: '광주광역시',
  daejeon: '대전광역시',
  ulsan: '울산광역시',
  sejong: '세종특별자치시',
}

function mergeRegionStats(districts: RegionStatDistrict[]) {
  return REGION_NODES.map(node => {
    let academyCount = 0
    if (METRO_NODE_IDS.has(node.id)) {
      const normalized = normalizeRegionName(node.region)
      academyCount = districts
        .filter(d => normalizeRegionName(d.region).includes(normalized) || normalized.includes(normalizeRegionName(d.region)))
        .reduce((sum, d) => sum + d.academy_count, 0)
    } else {
      academyCount = districts
        .filter(d => d.district === node.name)
        .reduce((sum, d) => sum + d.academy_count, 0)
    }
    return { ...node, academy_count: academyCount }
  })
}

// 실제 academy_count로 min-max 정규화한 gap_index. 백엔드 /region-stats가 이미 전국
// 시군구 단위로 정규화한 값을 주지만, 여기서는 REGION_NODES 20개로 범위를 좁혀 다시
// 계산해야 "이 20개 중 상대적 위치"라는 의미가 맞다(전국 250개 시군구 기준으로 정규화하면
// 값이 다 한쪽으로 몰림).
function recomputeGapIndexAndTier(nodes: ReturnType<typeof mergeRegionStats>) {
  const counts = nodes.map(n => n.academy_count)
  const lo = Math.min(...counts)
  const hi = Math.max(...counts)
  const span = hi - lo || 1
  const withGap = nodes.map(n => ({ ...n, gap_index: (n.academy_count - lo) / span }))
  const sorted = [...withGap].sort((a, b) => b.gap_index - a.gap_index)
  const q = Math.ceil(sorted.length / 4)
  const tierOf = (rank: number) => (rank < q ? 'S' : rank < q * 2 ? 'A' : rank < q * 3 ? 'B' : 'C') as 'S' | 'A' | 'B' | 'C'
  const rankById = new Map(sorted.map((n, i) => [n.id, i]))
  return withGap.map(n => ({ ...n, tier: tierOf(rankById.get(n.id)!) }))
}

async function buildRegionStatsFromFacilityCounts(): Promise<RegionStatDistrict[]> {
  const results = await Promise.all(REGION_NODES.map(async node => {
    const params = new URLSearchParams({
      facility_type: 'academy',
      limit: '1',
    })
    if (METRO_NODE_IDS.has(node.id)) params.set('region', METRO_REGION_NAME[node.id] || node.region)
    else params.set('district', node.name)

    const response = await fetchFromBackend<{ total?: number; matching_total?: number }>(
      `/education-facilities?${params.toString()}`,
    )
    return {
      region: node.region,
      district: node.name,
      academy_count: response?.data.matching_total ?? response?.data.total ?? 0,
      gap_index: 0,
    }
  }))
  return results
}

export async function GET() {
  let regionStats: RegionStatDistrict[] = []
  let loopStatus: any = null
  let source = 'fallback-empty'

  const statsResult = await fetchFromBackend<{ districts?: RegionStatDistrict[] }>('/region-stats')
  if (statsResult?.data.districts?.length) {
    regionStats = statsResult.data.districts
    source = `region-stats:${statsResult.baseUrl}`
  } else {
    const recoveredStats = await buildRegionStatsFromFacilityCounts()
    if (recoveredStats.some(r => r.academy_count > 0)) {
      regionStats = recoveredStats
      source = 'education-facilities-counts'
    }
  }

  const loopResult = await fetchFromBackend<any>('/loop-status')
  if (loopResult?.data) loopStatus = loopResult.data

  const merged = mergeRegionStats(regionStats)
  const nodes = recomputeGapIndexAndTier(merged)

  return NextResponse.json({
    regions: nodes,
    backend_region_count: regionStats.length,
    source,
    loop_status: loopStatus,
    updated_at: new Date().toISOString(),
  })
}
