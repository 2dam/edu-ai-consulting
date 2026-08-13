/**
 * /ads.txt — Google AdSense 인증 파일
 *
 * AdSense → 사이트 → 사이트 인증 에서 발급받은 내용이 자동으로 서빙됩니다.
 * 게시자 ID는 NEXT_PUBLIC_ADSENSE_PUBLISHER_ID 환경변수에서 읽습니다.
 *
 * 예시 출력:
 *   google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0
 *
 * 주의: 세 번째 토큰(DIRECT/RESELLER)과 네 번째 토큰(인증 ID)은
 * AdSense 계정의 'ads.txt' 안내 화면에 표시된 값을 그대로 사용하세요.
 */
import { NextRequest } from 'next/server'

// 실제 AdSense 계정에서 발급받은 인증 ID (Sellers.json / ads.txt 매핑용).
// AdSense → 사이트 → [도메인] → ads.txt 에 표시된 값을 그대로 입력.
const ADS_CERT_ID = 'f08c47fec0942fa0'

export const dynamic = 'force-static'

export function GET(req: NextRequest) {
  const publisherId = process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID || ''
  const body = publisherId
    ? `google.com, ${publisherId}, DIRECT, ${ADS_CERT_ID}\n`
    : `# AdSense 게시자 ID(NEXT_PUBLIC_ADSENSE_PUBLISHER_ID)가 설정되지 않았습니다.\n# AdSense 가입 후 .env.local 에 실제 pub-XXXXXXXXXXXXXXXX 값을 입력하세요.\n`

  return new Response(body, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=3600',
    },
  })
}
