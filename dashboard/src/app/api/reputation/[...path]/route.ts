import { NextRequest, NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

// 학원 평판 API 전체를 한 파일에서 프록시한다 (committee/run/route.ts와 같은 포워딩 패턴을
// 일반화). 관리 엔드포인트는 백엔드의 임시 인증(X-User-Id 헤더 + require_admin)에 맞춰
// 고정 관리자 id를 실어 보낸다 — 공개 설문 엔드포인트(surveys/*)는 백엔드가 이 헤더를
// 아예 보지 않으므로 그대로 둬도 무해하다.
//
// 주의: 이 프록시가 관리자 헤더를 "항상" 붙여 보내기 때문에, 별도 게이트가 없으면
// /reputation 페이지 URL을 아는 누구나 관리자 API를 그대로 쓸 수 있다. 그래서 surveys/*가
// 아닌 모든 경로는 ADMIN_ACCESS_TOKEN과 일치하는 X-Admin-Token 헤더가 있어야 통과한다.
const ADMIN_USER_ID = process.env.ADMIN_USER_ID ?? '1'

type Ctx = { params: Promise<{ path: string[] }> }

function isPublicPath(path: string[]): boolean {
  // 공개 설문 조회/응답(GET·POST /surveys/{token}[/responses])만 무인증 허용 — 백엔드의
  // require_admin 미적용 범위와 정확히 일치시킨다.
  return path[0] === 'surveys'
}

async function forward(request: NextRequest, path: string[]) {
  if (!isPublicPath(path)) {
    const adminToken = process.env.ADMIN_ACCESS_TOKEN
    const provided = request.headers.get('x-admin-token')
    if (!adminToken || provided !== adminToken) {
      return NextResponse.json({ detail: '관리자 인증이 필요합니다' }, { status: 401 })
    }
  }

  const search = new URL(request.url).search
  const target = `${BACKEND_URL}/reputation/${path.join('/')}${search}`

  const headers: Record<string, string> = { 'X-User-Id': ADMIN_USER_ID }
  let body: BodyInit | undefined

  if (!['GET', 'HEAD'].includes(request.method)) {
    const contentType = request.headers.get('content-type') || ''
    if (contentType.includes('multipart/form-data')) {
      // fetch가 FormData를 boundary 포함 Content-Type으로 알아서 직렬화하므로 직접 지정하지 않는다.
      body = await request.formData()
    } else {
      const text = await request.text()
      if (text) {
        headers['Content-Type'] = contentType || 'application/json'
        body = text
      }
    }
  }

  try {
    const res = await fetch(target, {
      method: request.method,
      headers,
      body,
      signal: AbortSignal.timeout(30000),
    })
    const buf = await res.arrayBuffer()
    const outHeaders: Record<string, string> = {
      'Content-Type': res.headers.get('content-type') || 'application/octet-stream',
    }
    const disposition = res.headers.get('content-disposition')
    if (disposition) outHeaders['Content-Disposition'] = disposition
    return new NextResponse(buf, { status: res.status, headers: outHeaders })
  } catch {
    return NextResponse.json({ detail: '백엔드 연결 실패 또는 시간 초과 (학원 평판 API)' }, { status: 502 })
  }
}

export async function GET(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
export async function POST(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
export async function PATCH(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
export async function DELETE(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
