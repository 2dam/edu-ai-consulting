import { useState } from "react";
import { ApiError } from "../../api/client";
import type { VoteResult } from "../../api/types";
import "./VoteButtons.css";

interface Props {
  upvoteCount: number;
  downvoteCount: number;
  onVote: (value: 1 | -1) => Promise<VoteResult>;
}

export function VoteButtons({ upvoteCount, downvoteCount, onVote }: Props) {
  const [counts, setCounts] = useState({ up: upvoteCount, down: downvoteCount });
  const [userVote, setUserVote] = useState<1 | -1 | 0>(0);
  const [error, setError] = useState<string | null>(null);

  async function handleVote(value: 1 | -1) {
    setError(null);
    try {
      const result = await onVote(value);
      setCounts({ up: result.upvote_count, down: result.downvote_count });
      setUserVote(result.user_vote);
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? "닉네임 등록 후 투표할 수 있어요" : "투표에 실패했습니다");
    }
  }

  return (
    <div className="vote-buttons">
      <button
        type="button"
        className={`vote-btn up ${userVote === 1 ? "active" : ""}`}
        onClick={() => handleVote(1)}
        aria-label="추천"
      >
        ▲
      </button>
      <span className="vote-score">{counts.up - counts.down}</span>
      <button
        type="button"
        className={`vote-btn down ${userVote === -1 ? "active" : ""}`}
        onClick={() => handleVote(-1)}
        aria-label="비추천"
      >
        ▼
      </button>
      {error && <span className="vote-error">{error}</span>}
    </div>
  );
}
