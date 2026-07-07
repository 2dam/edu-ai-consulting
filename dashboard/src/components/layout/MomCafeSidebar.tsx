import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { getBoards } from "../../api/momCafe";
import type { BoardOut } from "../../api/types";
import "./MomCafeSidebar.css";

export function MomCafeSidebar() {
  const [regionBoards, setRegionBoards] = useState<BoardOut[]>([]);
  const [showAllRegions, setShowAllRegions] = useState(false);

  useEffect(() => {
    getBoards()
      .then((boards) => setRegionBoards(boards.filter((b) => b.board_type === "region")))
      .catch(() => setRegionBoards([]));
  }, []);

  const visibleRegions = showAllRegions ? regionBoards : regionBoards.slice(0, 6);

  return (
    <aside className="mom-cafe-sidebar">
      <nav className="sidebar-nav">
        <NavLink to="/" end className="sidebar-link">
          🏠 전체 커뮤니티
        </NavLink>
        <NavLink to="/news" className="sidebar-link">
          📰 교육 뉴스
        </NavLink>
        <NavLink to="/mom-cafe/education" className="sidebar-link">
          🎓 교육 게시판
        </NavLink>
        <NavLink to="/mom-cafe/parenting" className="sidebar-link">
          👶 육아 게시판
        </NavLink>
        <NavLink to="/board/general" className="sidebar-link">
          💬 자유게시판
        </NavLink>
        <NavLink to="/admin" className="sidebar-link admin-link">
          🛠 관리자
        </NavLink>
      </nav>

      <div className="sidebar-section">
        <h3>지역 게시판</h3>
        <ul className="region-list">
          {visibleRegions.map((b) => (
            <li key={b.id}>
              <NavLink to={`/mom-cafe/region/${b.region?.length ? b.slug.replace(/^region-/, "") : b.slug}`}>
                {b.region ?? b.name}
              </NavLink>
            </li>
          ))}
        </ul>
        {regionBoards.length > 6 && (
          <button type="button" className="show-more-btn" onClick={() => setShowAllRegions((v) => !v)}>
            {showAllRegions ? "접기" : `+${regionBoards.length - 6}개 더보기`}
          </button>
        )}
      </div>
    </aside>
  );
}
