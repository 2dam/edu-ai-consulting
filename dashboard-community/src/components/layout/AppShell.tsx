import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";
import { getBoards } from "../../api/momCafe";
import { useUser } from "../../context/UserContext";
import { MomCafeSidebar } from "./MomCafeSidebar";
import { TrendingTopics } from "./TrendingTopics";
import "./AppShell.css";

function RegisterWidget() {
  const { user, register, logout } = useUser();
  const [nickname, setNickname] = useState("");
  const [regionSlug, setRegionSlug] = useState("");
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
    if (!nickname.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await register(nickname.trim(), regionSlug || undefined);
    } catch {
      setError("닉네임이 이미 사용 중이거나 등록에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="register-widget" onSubmit={handleSubmit}>
      <input
        placeholder="닉네임으로 시작하기"
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
      />
      <select value={regionSlug} onChange={(e) => setRegionSlug(e.target.value)}>
        <option value="">지역 선택(선택)</option>
        {regions.map((r) => (
          <option key={r.slug} value={r.slug}>
            {r.name}
          </option>
        ))}
      </select>
      <button type="submit" disabled={submitting || !nickname.trim()}>
        시작하기
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
          <Outlet />
        </main>
        <TrendingTopics />
      </div>
    </div>
  );
}
