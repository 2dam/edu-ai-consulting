import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import "./index.css";
import "./styles/global.css";
import App from "./App.tsx";
import { AdsConsentProvider } from "./lib/adsense";
import { AdConsentBanner } from "./components/AdConsentBanner";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AdsConsentProvider>
      <HashRouter>
        <App />
      </HashRouter>
      <AdConsentBanner />
    </AdsConsentProvider>
  </StrictMode>
);
