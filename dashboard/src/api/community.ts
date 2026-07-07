import { api } from "./client";
import type {
  CommentOut,
  CommunityPostDetail,
  CommunityPostOut,
  CurrentUser,
  FeedPage,
  ReportOut,
  ReportReason,
  VoteResult,
} from "./types";

export function registerUser(nickname: string, regionSlug?: string): Promise<CurrentUser> {
  return api.post<CurrentUser>("/community/users", { nickname, region_slug: regionSlug || null });
}

export function getCommunityFeed(params: {
  boardSlug?: string;
  sort?: "new" | "top";
  limit?: number;
  offset?: number;
}): Promise<FeedPage<CommunityPostOut>> {
  const q = new URLSearchParams();
  if (params.boardSlug) q.set("board_slug", params.boardSlug);
  if (params.sort) q.set("sort", params.sort);
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset) q.set("offset", String(params.offset));
  return api.get<FeedPage<CommunityPostOut>>(`/community/feed?${q.toString()}`);
}

export function getCommunityPost(id: number): Promise<CommunityPostDetail> {
  return api.get<CommunityPostDetail>(`/community/posts/${id}`);
}

export function createCommunityPost(boardSlug: string, title: string, body: string): Promise<CommunityPostOut> {
  return api.post<CommunityPostOut>("/community/posts", { board_slug: boardSlug, title, body });
}

export function addCommunityComment(postId: number, body: string, parentId?: number): Promise<CommentOut> {
  return api.post<CommentOut>(`/community/posts/${postId}/comments`, { body, parent_id: parentId ?? null });
}

export function voteCommunityPost(postId: number, value: 1 | -1): Promise<VoteResult> {
  return api.post<VoteResult>(`/community/posts/${postId}/vote`, { value });
}

export function voteComment(commentId: number, value: 1 | -1): Promise<VoteResult> {
  return api.post<VoteResult>(`/community/comments/${commentId}/vote`, { value });
}

export function reportCommunityPost(postId: number, reason: ReportReason, detail?: string): Promise<ReportOut> {
  return api.post<ReportOut>(`/community/posts/${postId}/report`, { reason, detail: detail || null });
}

export function getTrendingKeywords(): Promise<string[]> {
  return api.get<string[]>("/community/trending");
}

export interface RelatedPost {
  id: number;
  title: string;
}

export function getRelatedPosts(postId: number): Promise<RelatedPost[]> {
  return api.get<RelatedPost[]>(`/community/posts/${postId}/related`);
}
