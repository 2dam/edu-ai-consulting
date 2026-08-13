/**
 * AdSense 동의 관리 + 스크립트 로더 (Vite 커뮤니티앱)
 *
 * - 동의 전까지 광고 스크립트를 로드하지 않는다 (개인정보보호법/GDPR 대응).
 * - 플레이스홀더 게시자 ID(pub-0..)면 안전을 위해 로드하지 않는다.
 */
import { useEffect, useState, createContext, useContext } from "react";

const CONSENT_KEY = "edu-ai-consulting:ad-consent";
const ADS_ENABLED = import.meta.env.VITE_ADS_ENABLED !== "false";

export type ConsentState = "unknown" | "granted" | "denied";

export const AdConsentContext = createContext<{
  consent: ConsentState;
  grant: () => void;
  deny: () => void;
}>({
  consent: "unknown",
  grant: () => {},
  deny: () => {},
});

export function useAdConsent() {
  return useContext(AdConsentContext);
}

export function loadConsent(): ConsentState {
  if (typeof window === "undefined") return "unknown";
  const v = window.localStorage.getItem(CONSENT_KEY);
  return (v as ConsentState) || "unknown";
}

export function loadAdSenseScript(publisherId: string): void {
  if (typeof window === "undefined") return;
  if (!publisherId || publisherId.startsWith("pub-0")) return;
  if (window.document.getElementById("adsense-script")) return;

  const s = window.document.createElement("script");
  s.id = "adsense-script";
  s.async = true;
  s.crossOrigin = "anonymous";
  s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${publisherId}`;
  window.document.head.appendChild(s);
}

export function AdsConsentProvider({ children }: { children: React.ReactNode }) {
  const [consent, setConsent] = useState<ConsentState>("unknown");

  useEffect(() => {
    setConsent(loadConsent());
  }, []);

  useEffect(() => {
    const publisherId = import.meta.env.VITE_ADSENSE_PUBLISHER_ID || "";
    if (ADS_ENABLED && consent === "granted") {
      loadAdSenseScript(publisherId);
    }
  }, [consent]);

  const grant = () => {
    window.localStorage.setItem(CONSENT_KEY, "granted");
    setConsent("granted");
  };
  const deny = () => {
    window.localStorage.setItem(CONSENT_KEY, "denied");
    setConsent("denied");
  };

  return (
    <AdConsentContext.Provider value={{ consent, grant, deny }}>
      {children}
    </AdConsentContext.Provider>
  );
}
