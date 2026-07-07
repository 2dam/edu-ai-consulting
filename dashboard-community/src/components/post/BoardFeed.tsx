import { useEffect, useState } from "react";
import { getEducationBoard, getParentingBoard, getRegionBoard } from "../../api/momCafe";
import { communityPostToFeedItem } from "../../api/types";
import type { FeedItem } from "../../api/types";
import { CreatePostForm } from "./CreatePostForm";
import { PostCard } from "./PostCard";

interface Props {
  title: string;
  boardSlug: string;
  kind: "region" | "education" | "parenting";
  regionSlug?: string;
}

/** mom-cafe의 지역/교육/육아 게시판 페이지가 공유하는 피드 렌더링 — 백엔드의 _board_feed 헬퍼와 대응. */
export function BoardFeed({ title, boardSlug, kind, regionSlug }: Props) {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const fetchFeed =
      kind === "region" && regionSlug
        ? getRegionBoard(regionSlug)
        : kind === "education"
          ? getEducationBoard()
          : getParentingBoard();

    fetchFeed
      .then((page) => setItems(page.items.map(communityPostToFeedItem)))
      .finally(() => setLoading(false));
  }, [kind, regionSlug]);

  return (
    <div>
      <div className="page-toolbar">
        <h1 className="page-title">{title}</h1>
      </div>
      <CreatePostForm boardSlug={boardSlug} />
      {loading && <p className="loading-text">불러오는 중...</p>}
      {!loading && items.length === 0 && <p className="empty-text">아직 게시글이 없어요.</p>}
      {items.map((item) => (
        <PostCard key={item.id} item={item} />
      ))}
    </div>
  );
}
