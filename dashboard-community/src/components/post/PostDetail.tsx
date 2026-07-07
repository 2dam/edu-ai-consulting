import { type ReactNode, useState } from "react";
import { CommentForm } from "../comment/CommentForm";
import { CommentThread } from "../comment/CommentThread";
import { ReportButton } from "../common/ReportButton";
import { SourceLink } from "../common/SourceLink";
import { VoteButtons } from "../common/VoteButtons";
import type { CommentOut, ReportReason, VoteResult } from "../../api/types";
import { countComments, insertComment } from "../../utils/commentTree";
import { parseApiDate } from "../../utils/date";
import "./PostDetail.css";

interface Props {
  kind: "community" | "news";
  boardOrCategoryLabel: string;
  title: string;
  body: string;
  authorLabel: string;
  createdAt: string;
  upvoteCount: number;
  downvoteCount: number;
  sourceUrl?: string;
  fakeNewsRiskLabel?: string | null;
  initialComments: CommentOut[];
  onVote: (value: 1 | -1) => Promise<VoteResult>;
  onReport: (reason: ReportReason, detail?: string) => Promise<unknown>;
  onComment: (body: string, parentId?: number) => Promise<CommentOut>;
  extraActions?: ReactNode;
}

export function PostDetail({
  boardOrCategoryLabel,
  title,
  body,
  authorLabel,
  createdAt,
  upvoteCount,
  downvoteCount,
  sourceUrl,
  fakeNewsRiskLabel,
  initialComments,
  onVote,
  onReport,
  onComment,
  extraActions,
}: Props) {
  const [comments, setComments] = useState(initialComments);

  async function handleComment(commentBody: string, parentId?: number) {
    const created = await onComment(commentBody, parentId);
    setComments((prev) => insertComment(prev, created));
  }

  return (
    <article className="post-detail">
      <div className="post-detail-meta">
        <span className="post-detail-board">{boardOrCategoryLabel}</span>
        <span>{authorLabel}</span>
        <span>{parseApiDate(createdAt).toLocaleString("ko-KR")}</span>
      </div>
      <h1 className="post-detail-title">{title}</h1>
      {sourceUrl && <SourceLink sourceUrl={sourceUrl} fakeNewsRiskLabel={fakeNewsRiskLabel} />}
      <p className="post-detail-body">{body}</p>

      {extraActions}

      <div className="post-detail-actions">
        <VoteButtons upvoteCount={upvoteCount} downvoteCount={downvoteCount} onVote={onVote} />
        <ReportButton onReport={onReport} />
      </div>

      <section className="post-detail-comments">
        <h2>댓글 {countComments(comments)}</h2>
        <CommentForm onSubmit={(commentBody) => handleComment(commentBody)} />
        <CommentThread comments={comments} onReply={(parentId, replyBody) => handleComment(replyBody, parentId)} />
      </section>
    </article>
  );
}
