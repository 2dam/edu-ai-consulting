import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'EduIntel — 한국 교육 인텔리전스',
  description: 'AI 빅데이터 기반 전국 교육격차 분석 플랫폼',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}
