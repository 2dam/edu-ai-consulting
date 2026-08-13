/**
 * AdBanner — 반응형 Google AdSense 광고 컴포넌트 (Next.js)
 *
 * 사용법:
 *   <AdBanner slot="1234567890" format="auto" />          // 지정 광고단위(슬롯 ID 필요)
 *   <AdBanner auto />                                      // 자동 광고 플레이스홀더
 *   <AdBanner slot="..." className="my-ad" style={...} />  // 위치/크기 커스텀
 *
 * 동작:
 *   - 쿠키/개인정보 동의 전에는 렌더되지 않는다.
 *   - 게시자 ID 미설정(플레이스홀더) 상태에서는 빈 컨테이너를 둔다(레이아웃 유지).
 *   - data-full-width-responsive 로 모바일에서 꽉 찬 폭 광고를 허용한다.
 */
'use client'

import { useEffect, useRef } from 'react'
import { useAdConsent } from '@/lib/adsense'

type Props = {
  /** AdSense 광고단위 슬롯 ID (AdSense → 광고 → 광고단위에서 복사). 자동 광고는 생략. */
  slot?: string
  /** 광고 형식. 기본 'auto' (반응형). */
  format?: 'auto' | 'rectangle' | 'vertical' | 'horizontal'
  /** 자동 광고 모드(슬롯 없이 Google이 위치 선택). */
  auto?: boolean
  className?: string
  style?: React.CSSProperties
  /** 광고가 안 뜰 때 보여줄 최소 높이(레이아웃 시프트 방지). px. 기본 100. */
  minHeight?: number
}

export default function AdBanner({
  slot,
  format = 'auto',
  auto = false,
  className,
  style,
  minHeight = 100,
}: Props) {
  const { consent } = useAdConsent()
  const ref = useRef<HTMLModElement>(null)
  const publisherId = process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID || ''

  useEffect(() => {
    const adsEnabled = process.env.NEXT_PUBLIC_ADS_ENABLED !== 'false'
    const realId = publisherId && !publisherId.startsWith('pub-0')
    if (!adsEnabled || consent !== 'granted' || !realId) return
    // AdSense 스크립트가 로드된 뒤 광고를 초기화한다.
    try {
      if (typeof window !== 'undefined' && (window as any).adsbygoogle) {
        ;((window as any).adsbygoogle as any[]).push({})
      }
    } catch {
      /* 초기화 중복 호출은 무시 */
    }
  }, [consent, publisherId, slot])

  const adsEnabled = process.env.NEXT_PUBLIC_ADS_ENABLED !== 'false'
  const show = adsEnabled && consent === 'granted'

  if (!show) {
    // 동의 전/비활성 시 레이아웃 시프트 방지를 위한 여백 컨테이너
    return (
      <div
        aria-hidden
        className={className}
        style={{ minHeight, width: '100%', ...style }}
      />
    )
  }

  return (
    <ins
      ref={ref}
      className={`adsbygoogle ${className || ''}`}
      style={{ display: 'block', width: '100%', minHeight, ...style }}
      data-ad-slot={auto ? undefined : slot}
      data-ad-format={auto ? undefined : format}
      data-full-width-responsive="true"
    />
  )
}
