import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getBoards } from "../api/momCafe";
import { getCommunityFeed } from "../api/community";
import { communityPostToFeedItem } from "../api/types";
import type { FeedItem } from "../api/types";
import { CreatePostForm } from "../components/post/CreatePostForm";
import { PostCard } from "../components/post/PostCard";

/** 자유게시판 등 범용 커뮤니티 게시판 — /board/:slug */
export function BoardPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [boardName, setBoardName] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    Promise.all([
      getCommunityFeed({ boardSlug: slug }),
      getBoards().then((boards) => boards.find((b) => b.slug === slug)?.name ?? slug),
    ])
      .then(([page, name]) => {
        setItems(page.items.map(communityPostToFeedItem));
        setBoardName(name);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  if (!slug) return null;

  return (
    <div>
      <div className="page-toolbar">
        <h1 className="page-title">{boardName}</h1>
      </div>
      <CreatePostForm boardSlug={slug} />
      {loading && <p className="loading-text">불러오는 중...</p>}
      {!loading && items.length === 0 && <p className="empty-text">아직 게시글이 없어요.</p>}
      {items.map((item) => (
        <PostCard key={item.id} item={item} />
      ))}
    </div>
  );
}
