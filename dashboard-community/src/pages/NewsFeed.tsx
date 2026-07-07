import { useEffect, useState } from "react";
import { getNewsFeed } from "../api/news";
import { newsPostToFeedItem } from "../api/types";
import type { FeedItem } from "../api/types";
import { PostCard } from "../components/post/PostCard";

const CATEGORIES = ["전체", "정책", "입시", "트렌드"];

export function NewsFeed() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [category, setCategory] = useState("전체");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getNewsFeed({ category: category === "전체" ? undefined : category })
      .then((page) => setItems(page.items.map(newsPostToFeedItem)))
      .finally(() => setLoading(false));
  }, [category]);

  return (
    <div>
      <div className="page-toolbar">
        <h1 className="page-title">교육 뉴스</h1>
      </div>
      <div className="category-filter">
        {CATEGORIES.map((c) => (
          <button key={c} className={category === c ? "active" : ""} onClick={() => setCategory(c)}>
            {c}
          </button>
        ))}
      </div>
      {loading && <p className="loading-text">불러오는 중...</p>}
      {!loading && items.length === 0 && <p className="empty-text">아직 등록된 뉴스가 없어요.</p>}
      {items.map((item) => (
        <PostCard key={item.id} item={item} />
      ))}
    </div>
  );
}
