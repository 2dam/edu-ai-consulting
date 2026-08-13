/**
 * AdBanner — 반응형 Google AdSense 광고 컴포넌트 (Vite/React)
 *
 * 사용법:
 *   <AdBanner slot="1234567890" />        // 지정 광고단위
 *   <AdBanner auto />                      // 자동 광고
 *   <AdBanner slot="..." className="x" />  // 위치 커스텀
 */
import { useEffect, useRef } from "react";
import { useAdConsent } from "../lib/adsense";

type Props = {
  slot?: string;
  format?: "auto" | "rectangle" | "vertical" | "horizontal";
  auto?: boolean;
  className?: string;
  minHeight?: number;
};

export function AdBanner({
  slot,
  format = "auto",
  auto = false,
  className,
  minHeight = 100,
}: Props) {
  const { consent } = useAdConsent();
  const ref = useRef<HTMLModElement>(null);
  const publisherId = import.meta.env.VITE_ADSENSE_PUBLISHER_ID || "";

  useEffect(() => {
    const adsEnabled = import.meta.env.VITE_ADS_ENABLED !== "false";
    const realId = publisherId && !publisherId.startsWith("pub-0");
    if (!adsEnabled || consent !== "granted" || !realId) return;
    try {
      if (typeof window !== "undefined" && (window as any).adsbygoogle) {
        (window as any).adsbygoogle.push({});
      }
    } catch {
      /* 중복 push 무시 */
    }
  }, [consent, publisherId, slot]);

  const adsEnabled = import.meta.env.VITE_ADS_ENABLED !== "false";
  const show = adsEnabled && consent === "granted";

  if (!show) {
    return (
      <div
        aria-hidden
        className={className}
        style={{ minHeight, width: "100%", margin: "16px 0" }}
      />
    );
  }

  return (
    <ins
      ref={ref}
      className={`adsbygoogle ${className || ''}`}
      style={{ display: 'block', width: '100%', minHeight, margin: '16px 0' }}
      data-ad-slot={auto ? undefined : slot}
      data-ad-format={auto ? undefined : format}
      data-full-width-responsive="true"
    />
  )
}
