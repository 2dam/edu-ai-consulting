import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  addNewsComment,
  getDebateSummary,
  getNewsDetail,
  reportNews,
  summarizeNews,
  voteNews,
  type DebateSummary,
} from "../api/news";
import type { NewsPostDetail } from "../api/types";
import { PostDetail } from "../components/post/PostDetail";

export function NewsDetailPage() {
  const { id } = useParams<{ id: string }>();
  const newsId = Number(id);
  const [news, setNews] = useState<NewsPostDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);
  const [debate, setDebate] = useState<DebateSummary | null>(null);
  const [debateLoading, setDebateLoading] = useState(false);
  const [debateError, setDebateError] = useState<string | null>(null);

  useEffect(() => {
    getNewsDetail(newsId)
      .then(setNews)
      .catch(() => setNotFound(true));
  }, [newsId]);

  async function handleSummarize() {
    setSummarizing(true);
    try {
      const result = await summarizeNews(newsId);
      setSummary(result.summary);
    } catch {
      setSummary("요약 생성에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setSummarizing(false);
    }
  }

  async function handleDebateSummary() {
    setDebateLoading(true);
    setDebateError(null);
    try {
      const result = await getDebateSummary(newsId);
      setDebate(result);
    } catch {
      setDebateError("아직 댓글이 충분하지 않거나 요약에 실패했습니다.");
    } finally {
      setDebateLoading(false);
    }
  }

  if (notFound) return <p className="empty-text">뉴스를 찾을 수 없어요.</p>;
  if (!news) return <p className="loading-text">불러오는 중...</p>;

  return (
    <PostDetail
      kind="news"
      boardOrCategoryLabel={news.category ?? "뉴스"}
      title={news.title}
      body={news.body_text ?? ""}
      authorLabel={news.source_name ?? "출처 미상"}
      createdAt={news.created_at}
      upvoteCount={news.upvote_count}
      downvoteCount={news.downvote_count}
      sourceUrl={news.source_url}
      fakeNewsRiskLabel={news.fake_news_risk_label}
      initialComments={news.comments}
      onVote={(value) => voteNews(newsId, value)}
      onReport={(reason, detail) => reportNews(newsId, reason, detail)}
      onComment={(body, parentId) => addNewsComment(newsId, body, parentId)}
      extraActions={
        <div className="ai-panel">
          <h3>AI 요약</h3>
          {!summary && (
            <button type="button" onClick={handleSummarize} disabled={summarizing}>
              {summarizing ? "요약 생성 중..." : "AI 기사 요약 보기"}
            </button>
          )}
          {summary && <p>{summary}</p>}

          <h3 style={{ marginTop: 12 }}>AI 토론 요약</h3>
          {!debate && (
            <button type="button" onClick={handleDebateSummary} disabled={debateLoading}>
              {debateLoading ? "분석 중..." : "댓글 토론 요약 보기"}
            </button>
          )}
          {debateError && <p style={{ color: "#e11d48" }}>{debateError}</p>}
          {debate && (
            <div>
              <p>{debate.comment_summary}</p>
              <strong>찬성 의견</strong>
              <ul>
                {debate.agree.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
              <strong>반대 의견</strong>
              <ul>
                {debate.disagree.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      }
    />
  );
}
