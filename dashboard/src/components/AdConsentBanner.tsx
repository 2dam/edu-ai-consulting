/**
 * AdConsentBanner — 쿠키/개인정보 동의 배너 (광고 표시 전 필수)
 *
 * - 방문자가 '동의'해야만 AdSense 스크립트가 로드된다 (개인정보보호법/GDPR 대응).
 * - '거부' 시 광고는 영구 비노출(세션保持).
 * - 이미 선택한 경우 배너는 나타나지 않는다.
 */
'use client'

import { useAdConsent } from '@/lib/adsense'

export default function AdConsentBanner() {
  const { consent, grant, deny } = useAdConsent()
  if (consent !== 'unknown') return null

  return (
    <div
      role="dialog"
      aria-label="쿠키 및 개인정보 처리 동의"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: '#0f172a',
        color: '#e2e8f0',
        padding: '14px 18px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '12px',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '14px',
        boxShadow: '0 -2px 12px rgba(0,0,0,0.3)',
      }}
    >
      <span style={{ flex: 1, minWidth: 240 }}>
        본 사이트는 Google AdSense를 통해 맞춤형 광고를 제공합니다. 광고 맞춤화를 위해
        쿠키와 방문 기록이 수집·처리될 수 있습니다. 동의하시겠습니까?
      </span>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={deny}
          style={{
            background: 'transparent',
            color: '#cbd5e1',
            border: '1px solid #475569',
            borderRadius: 6,
            padding: '8px 14px',
            cursor: 'pointer',
          }}
        >
          거부
        </button>
        <button
          onClick={grant}
          style={{
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '8px 14px',
            cursor: 'pointer',
          }}
        >
          동의
        </button>
      </div>
    </div>
  )
}
