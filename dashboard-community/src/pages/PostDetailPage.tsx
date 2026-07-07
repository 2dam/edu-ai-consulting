import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  addCommunityComment,
  getCommunityPost,
  getRelatedPosts,
  reportCommunityPost,
  voteCommunityPost,
  type RelatedPost,
} from "../api/community";
import type { CommunityPostDetail } from "../api/types";
import { PostDetail } from "../components/post/PostDetail";

export function PostDetailPage() {
  const { id } = useParams<{ id: string }>();
  const postId = Number(id);
  const [post, setPost] = useState<CommunityPostDetail | null>(null);
  const [related, setRelated] = useState<RelatedPost[]>([]);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    getCommunityPost(postId)
      .then(setPost)
      .catch(() => setNotFound(true));
    getRelatedPosts(postId)
      .then(setRelated)
      .catch(() => setRelated([]));
  }, [postId]);

  if (notFound) return <p className="empty-text">게시글을 찾을 수 없어요.</p>;
  if (!post) return <p className="loading-text">불러오는 중...</p>;

  return (
    <div>
      <PostDetail
        kind="community"
        boardOrCategoryLabel={post.board_slug}
        title={post.title}
        body={post.body}
        authorLabel={post.author_nickname}
        createdAt={post.created_at}
        upvoteCount={post.upvote_count}
        downvoteCount={post.downvote_count}
        initialComments={post.comments}
        onVote={(value) => voteCommunityPost(postId, value)}
        onReport={(reason, detail) => reportCommunityPost(postId, reason, detail)}
        onComment={(body, parentId) => addCommunityComment(postId, body, parentId)}
      />
      {related.length > 0 && (
        <section className="related-posts">
          <h3>관련 게시글</h3>
          <ul>
            {related.map((r) => (
              <li key={r.id}>
                <Link to={`/posts/${r.id}`}>{r.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
