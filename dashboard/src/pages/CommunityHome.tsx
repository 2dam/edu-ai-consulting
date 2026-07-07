import { useEffect, useState } from "react";
import { getCommunityFeed } from "../api/community";
import { communityPostToFeedItem } from "../api/types";
import type { FeedItem } from "../api/types";
import { CreatePostForm } from "../components/post/CreatePostForm";
import { PostCard } from "../components/post/PostCard";

export function CommunityHome() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [sort, setSort] = useState<"new" | "top">("new");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCommunityFeed({ sort })
      .then((page) => setItems(page.items.map(communityPostToFeedItem)))
      .finally(() => setLoading(false));
  }, [sort]);

  return (
    <div>
      <div className="page-toolbar">
        <h1 className="page-title">전체 커뮤니티</h1>
        <div className="sort-toggle">
          <button className={sort === "new" ? "active" : ""} onClick={() => setSort("new")}>
            최신순
          </button>
          <button className={sort === "top" ? "active" : ""} onClick={() => setSort("top")}>
            인기순
          </button>
        </div>
      </div>
      <CreatePostForm boardSlug="general" />
      {loading && <p className="loading-text">불러오는 중...</p>}
      {!loading && items.length === 0 && <p className="empty-text">아직 게시글이 없어요.</p>}
      {items.map((item) => (
        <PostCard key={`${item.kind}-${item.id}`} item={item} />
      ))}
    </div>
  );
}
