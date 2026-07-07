import { useState } from "react";
import { voteComment } from "../../api/community";
import type { CommentOut } from "../../api/types";
import { parseApiDate } from "../../utils/date";
import { VoteButtons } from "../common/VoteButtons";
import { CommentForm } from "./CommentForm";
import "./CommentThread.css";

interface Props {
  comments: CommentOut[];
  onReply: (parentId: number, body: string) => Promise<unknown>;
  depth?: number;
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

function CommentNode({
  comment,
  onReply,
  depth,
}: {
  comment: CommentOut;
  onReply: (parentId: number, body: string) => Promise<unknown>;
  depth: number;
}) {
  const [replying, setReplying] = useState(false);
  const isHidden = comment.moderation_status !== "visible";

  return (
    <li className="comment-node" style={{ marginLeft: depth * 20 }}>
      <div className={`comment-body-row ${isHidden ? "hidden-content" : ""}`}>
        <span className="comment-author">{comment.author_nickname}</span>
        <span className="comment-time">{timeAgo(comment.created_at)}</span>
        {comment.toxicity_flag && (
          <span className="toxicity-badge" title="AI가 부적절할 수 있다고 참고 표시한 댓글입니다 (자동 삭제되지 않음)">
            ⚠ AI 검토 필요(참고용)
          </span>
        )}
      </div>
      <p className="comment-text">{isHidden ? "(운영자에 의해 숨김 처리된 댓글입니다)" : comment.body}</p>
      <div className="comment-actions">
        <VoteButtons
          upvoteCount={comment.upvote_count}
          downvoteCount={comment.downvote_count}
          onVote={(value) => voteComment(comment.id, value)}
        />
        <button type="button" className="comment-reply-toggle" onClick={() => setReplying((v) => !v)}>
          답글
        </button>
      </div>
      {replying && (
        <CommentForm
          compact
          placeholder="답글을 입력하세요"
          onSubmit={async (body) => {
            await onReply(comment.id, body);
            setReplying(false);
          }}
        />
      )}
      {comment.replies.length > 0 && (
        <ul className="comment-list">
          {comment.replies.map((reply) => (
            <CommentNode key={reply.id} comment={reply} onReply={onReply} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function CommentThread({ comments, onReply }: Props) {
  if (comments.length === 0) {
    return <p className="comment-empty">아직 댓글이 없어요. 첫 댓글을 남겨보세요!</p>;
  }

  return (
    <ul className="comment-list root">
      {comments.map((c) => (
        <CommentNode key={c.id} comment={c} onReply={onReply} depth={0} />
      ))}
    </ul>
  );
}
