import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  addNewsComment,
  getDebateSummary,
  getNewsDetail,
  getSentimentAnalysis,
  reportNews,
  summarizeNews,
  voteNews,
  type DebateSummary,
  type SentimentAnalysis,
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
  const [sentiment, setSentiment] = useState<SentimentAnalysis | null>(null);
  const [sentimentLoading, setSentimentLoading] = useState(false);
  const [sentimentError, setSentimentError] = useState<string | null>(null);

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

  async function handleSentiment() {
    setSentimentLoading(true);
    setSentimentError(null);
    try {
      const result = await getSentimentAnalysis(newsId);
      setSentiment(result);
    } catch {
      setSentimentError("여론 평가에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setSentimentLoading(false);
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

          <h3 style={{ marginTop: 12 }}>여론 평가</h3>
          {!sentiment && (
            <button type="button" onClick={handleSentiment} disabled={sentimentLoading}>
              {sentimentLoading ? "분석 중..." : "기사·댓글 여론 분석 보기"}
            </button>
          )}
          {sentimentError && <p style={{ color: "#e11d48" }}>{sentimentError}</p>}
          {sentiment && (
            <div>
              <p>
                종합 여론:{" "}
                <strong style={{ color: SENTIMENT_COLOR[sentiment.overall_label] }}>
                  {SENTIMENT_LABEL_KO[sentiment.overall_label]}
                </strong>{" "}
                ({sentiment.total_analyzed}건 분석,{" "}
                {sentiment.method === "finbert" ? "FinBERT" : "규칙 기반"})
              </p>
              <ul>
                <li style={{ color: SENTIMENT_COLOR.positive }}>긍정 {sentiment.positive_count}건</li>
                <li style={{ color: SENTIMENT_COLOR.neutral }}>중립 {sentiment.neutral_count}건</li>
                <li style={{ color: SENTIMENT_COLOR.negative }}>부정 {sentiment.negative_count}건</li>
              </ul>
            </div>
          )}
        </div>
      }
    />
  );
}

const SENTIMENT_LABEL_KO: Record<SentimentAnalysis["overall_label"], string> = {
  positive: "긍정적",
  neutral: "중립적",
  negative: "부정적",
};

const SENTIMENT_COLOR: Record<SentimentAnalysis["overall_label"], string> = {
  positive: "#16a34a",
  neutral: "#6b7280",
  negative: "#e11d48",
};
