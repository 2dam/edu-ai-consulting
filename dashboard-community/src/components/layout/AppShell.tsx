import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";
import { getBoards } from "../../api/momCafe";
import { useUser } from "../../context/UserContext";
import { MomCafeSidebar } from "./MomCafeSidebar";
import { TrendingTopics } from "./TrendingTopics";
import { AdBanner } from "../../components/AdBanner";
import "./AppShell.css";

function RegisterWidget() {
  const { user, register, login, logout } = useUser();
  const [nickname, setNickname] = useState("");
  const [regionSlug, setRegionSlug] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [regions, setRegions] = useState<{ slug: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getBoards()
      .then((boards) =>
        setRegions(
          boards
            .filter((b) => b.board_type === "region" && b.region)
            .map((b) => ({ slug: b.slug.replace(/^region-/, ""), name: b.region as string }))
        )
      )
      .catch(() => setRegions([]));
  }, []);

  if (user) {
    return (
      <div className="register-widget">
        <span className="current-user">👤 {user.nickname}</span>
        <button type="button" className="logout-btn" onClick={logout}>
          로그아웃
        </button>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!nickname.trim() || password.length < 10) return;
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "register") await register(nickname.trim(), password, regionSlug || undefined);
      else await login(nickname.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "인증에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="register-widget" onSubmit={handleSubmit}>
      <input
        placeholder="닉네임"
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
      />
      <input
        type="password"
        autoComplete={mode === "login" ? "current-password" : "new-password"}
        placeholder="비밀번호(10자 이상)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {mode === "register" && <select value={regionSlug} onChange={(e) => setRegionSlug(e.target.value)}>
        <option value="">지역 선택(선택)</option>
        {regions.map((r) => (
          <option key={r.slug} value={r.slug}>
            {r.name}
          </option>
        ))}
      </select>}
      <button type="submit" disabled={submitting || !nickname.trim() || password.length < 10}>
        {mode === "login" ? "로그인" : "가입"}
      </button>
      <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
        {mode === "login" ? "회원가입" : "로그인으로"}
      </button>
      {error && <span className="register-error">{error}</span>}
    </form>
  );
}

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-logo">
          AI 교육뉴스 커뮤니티 · 맘카페
        </Link>
        <RegisterWidget />
      </header>
      <div className="app-body">
        <MomCafeSidebar />
        <main className="app-main">
          {/* 메인 콘텐츠 상단 광고 — 초기 자동 광고(auto) 모드. 슬롯 지정 시 아래 auto 빼고 slot 사용 */}
          <AdBanner auto className="ad-top" />
          <Outlet />
        </main>
        <TrendingTopics />
      </div>
    </div>
  );
}
