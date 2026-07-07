import { api } from "./client";
import type {
  CommentOut,
  FeedPage,
  NewsPostDetail,
  NewsPostOut,
  NewsSummaryOut,
  ReportOut,
  ReportReason,
  VoteResult,
} from "./types";

export interface DebateSummary {
  news_post_id: number;
  comment_summary: string;
  agree: string[];
  disagree: string[];
}

export function getNewsFeed(params: {
  category?: string;
  regionSlug?: string;
  limit?: number;
  offset?: number;
}): Promise<FeedPage<NewsPostOut>> {
  const q = new URLSearchParams();
  if (params.category) q.set("category", params.category);
  if (params.regionSlug) q.set("region_slug", params.regionSlug);
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset) q.set("offset", String(params.offset));
  return api.get<FeedPage<NewsPostOut>>(`/news/feed?${q.toString()}`);
}

export function getNewsDetail(id: number): Promise<NewsPostDetail> {
  return api.get<NewsPostDetail>(`/news/${id}`);
}

export function summarizeNews(id: number): Promise<NewsSummaryOut> {
  return api.post<NewsSummaryOut>(`/news/${id}/summarize`);
}

export function getDebateSummary(id: number): Promise<DebateSummary> {
  return api.post<DebateSummary>(`/news/${id}/debate-summary`);
}

export function addNewsComment(newsId: number, body: string, parentId?: number): Promise<CommentOut> {
  return api.post<CommentOut>(`/news/${newsId}/comments`, { body, parent_id: parentId ?? null });
}

export function voteNews(newsId: number, value: 1 | -1): Promise<VoteResult> {
  return api.post<VoteResult>(`/news/${newsId}/vote`, { value });
}

export function reportNews(newsId: number, reason: ReportReason, detail?: string): Promise<ReportOut> {
  return api.post<ReportOut>(`/news/${newsId}/report`, { reason, detail: detail || null });
}
