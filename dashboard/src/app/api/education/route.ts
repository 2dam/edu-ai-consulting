import { NextResponse } from 'next/server'
import { REGION_NODES, GANGNAM_ACADEMIES } from '@/lib/data'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'
const BACKEND_TIMEOUT_MS = 3500

export async function GET() {
  // FastAPI 백엔드에서 실제 수집 데이터 병합
  let backendRecords: any[] = []
  let loopStatus: any = null

  try {
    const [recRes, loopRes] = await Promise.all([
      fetch(`${BACKEND}/records?limit=200`, {
        next: { revalidate: 60 },
        signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
      }),
      fetch(`${BACKEND}/loop-status`, {
        next: { revalidate: 30 },
        signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
      }),
    ])
    if (recRes.ok) backendRecords = await recRes.json()
    if (loopRes.ok) loopStatus = await loopRes.json()
  } catch {
    // 백엔드 미실행 시 기본 데이터만 반환
  }

  // 실제 수집된 학원 데이터를 지역 노드에 병합
  const academyCounts: Record<string, number> = {}
  for (const rec of backendRecords) {
    const region = rec.data?.region || rec.data?.academy_name || ''
    const key = Object.values(REGION_NODES).find(n =>
      region.includes(n.region) || region.includes(n.name)
    )?.id
    if (key) academyCounts[key] = (academyCounts[key] || 0) + 1
  }

  const nodes = REGION_NODES.map(n => ({
    ...n,
    crawled_count: academyCounts[n.id] || 0,
  }))

  return NextResponse.json({
    regions: nodes,
    gangnam_academies: GANGNAM_ACADEMIES,
    backend_record_count: backendRecords.length,
    loop_status: loopStatus,
    updated_at: new Date().toISOString(),
  })
}
