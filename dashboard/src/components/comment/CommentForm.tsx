import { useState } from "react";
import { useUser } from "../../context/UserContext";
import "./CommentForm.css";

interface Props {
  onSubmit: (body: string) => Promise<unknown>;
  placeholder?: string;
  compact?: boolean;
}

export function CommentForm({ onSubmit, placeholder, compact }: Props) {
  const { user } = useUser();
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user) {
    return <p className="comment-form-login-hint">닉네임을 등록하면 댓글을 남길 수 있어요.</p>;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(body.trim());
      setBody("");
    } catch {
      setError("댓글 작성에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className={`comment-form ${compact ? "compact" : ""}`} onSubmit={handleSubmit}>
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder ?? "댓글을 입력하세요"}
        rows={compact ? 1 : 3}
      />
      <button type="submit" disabled={submitting || !body.trim()}>
        등록
      </button>
      {error && <span className="comment-form-error">{error}</span>}
    </form>
  );
}
