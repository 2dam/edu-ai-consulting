import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCommunityPost } from "../../api/community";
import { useUser } from "../../context/UserContext";
import "./CreatePostForm.css";

interface Props {
  boardSlug: string;
  onCreated?: () => void;
}

export function CreatePostForm({ boardSlug, onCreated }: Props) {
  const { user } = useUser();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user) {
    return <p className="create-post-login-hint">닉네임을 등록하면 글을 쓸 수 있어요.</p>;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const post = await createCommunityPost(boardSlug, title.trim(), body.trim());
      setTitle("");
      setBody("");
      onCreated?.();
      navigate(`/posts/${post.id}`);
    } catch {
      setError("게시글 작성에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="create-post-form" onSubmit={handleSubmit}>
      <input
        className="create-post-title"
        placeholder="제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        className="create-post-body"
        placeholder="내용을 입력하세요"
        rows={5}
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <div className="create-post-footer">
        {error && <span className="create-post-error">{error}</span>}
        <button type="submit" disabled={submitting || !title.trim() || !body.trim()}>
          게시글 작성
        </button>
      </div>
    </form>
  );
}
