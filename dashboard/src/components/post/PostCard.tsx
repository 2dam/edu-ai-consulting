import { Link } from "react-router-dom";
import type { FeedItem } from "../../api/types";
import { parseApiDate } from "../../utils/date";
import { SourceLink } from "../common/SourceLink";
import "./PostCard.css";

interface Props {
  item: FeedItem;
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - parseApiDate(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "방금 전";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

export function PostCard({ item }: Props) {
  const detailPath = item.kind === "community" ? `/posts/${item.id}` : `/news/${item.id}`;

  return (
    <article className="post-card">
      <div className="post-card-meta">
        <span className="post-card-board">{item.boardOrCategoryLabel}</span>
        <span className="post-card-author">{item.authorLabel}</span>
        <span className="post-card-time">{timeAgo(item.createdAt)}</span>
      </div>
      <Link to={detailPath} className="post-card-title">
        {item.title}
      </Link>
      <p className="post-card-preview">{item.bodyPreview}</p>
      {item.kind === "news" && item.sourceUrl && (
        <SourceLink sourceUrl={item.sourceUrl} fakeNewsRiskLabel={item.fakeNewsRiskLabel} />
      )}
      <div className="post-card-stats">
        <span>👍 {item.upvoteCount - item.downvoteCount}</span>
        <span>💬 {item.commentCount}</span>
      </div>
    </article>
  );
}
