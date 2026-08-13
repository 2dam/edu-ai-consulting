/**
 * AdSense 동의 관리 + 스크립트 로더 (GDPR / 개인정보보호법 대응)
 *
 * - 방문자가 쿠키/개인정보 동의를 하기 전까지는 광고 스크립트를 로드하지 않는다.
 * - 동의 여부는 localStorage 에 저장하여 새로고침해도 유지된다.
 * - 게시자 ID(NEXT_PUBLIC_ADSENSE_PUBLISHER_ID)가 비어있거나
 *   플레이스홀더(pub-0..)이면 스크립트를 로드하지 않는다 (승인 전 안전 기본값).
 */
'use client'

import { useEffect, useState, createContext, useContext } from 'react'

const CONSENT_KEY = 'edu-ai-consulting:ad-consent'
const ADS_ENABLED = process.env.NEXT_PUBLIC_ADS_ENABLED !== 'false' // 기본 활성

export type ConsentState = 'unknown' | 'granted' | 'denied'

export const AdConsentContext = createContext<{
  consent: ConsentState
  grant: () => void
  deny: () => void
}>({
  consent: 'unknown',
  grant: () => {},
  deny: () => {},
})

export function useAdConsent() {
  return useContext(AdConsentContext)
}

export function loadConsent(): ConsentState {
  if (typeof window === 'undefined') return 'unknown'
  const v = window.localStorage.getItem(CONSENT_KEY)
  return (v as ConsentState) || 'unknown'
}

/** AdSense 자동 광고 스크립트를 한 번만 로드한다. */
export function loadAdSenseScript(publisherId: string): void {
  if (typeof window === 'undefined') return
  if (!publisherId || publisherId.startsWith('pub-0')) return // 플레이스홀더면 로드 안 함
  if (window.document.getElementById('adsense-script')) return // 중복 로드 방지

  const s = window.document.createElement('script')
  s.id = 'adsense-script'
  s.async = true
  s.crossOrigin = 'anonymous'
  s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${publisherId}`
  window.document.head.appendChild(s)
}

export function AdsConsentProvider({ children }: { children: React.ReactNode }) {
  const [consent, setConsent] = useState<ConsentState>('unknown')

  useEffect(() => {
    setConsent(loadConsent())
  }, [])

  useEffect(() => {
    const publisherId = process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID || ''
    if (ADS_ENABLED && consent === 'granted') {
      loadAdSenseScript(publisherId)
    }
  }, [consent])

  const grant = () => {
    window.localStorage.setItem(CONSENT_KEY, 'granted')
    setConsent('granted')
  }
  const deny = () => {
    window.localStorage.setItem(CONSENT_KEY, 'denied')
    setConsent('denied')
  }

  return (
    <AdConsentContext.Provider value={{ consent, grant, deny }}>
      {children}
    </AdConsentContext.Provider>
  )
}
