export type ModerationStatus = "visible" | "hidden" | "deleted";
export type ReportReason = "spam" | "abuse" | "personal_info" | "fake_news" | "other";

export interface CurrentUser {
  id: number;
  nickname: string;
  region: string | null;
  level: string | null;
}

export interface BoardOut {
  id: number;
  slug: string;
  name: string;
  board_type: "general" | "education" | "parenting" | "region" | "news";
  region: string | null;
}

export interface CommentOut {
  id: number;
  author_nickname: string;
  body: string;
  parent_id: number | null;
  upvote_count: number;
  downvote_count: number;
  toxicity_flag: boolean;
  moderation_status: ModerationStatus;
  created_at: string;
  replies: CommentOut[];
}

export interface CommunityPostOut {
  id: number;
  kind: "post";
  board_slug: string;
  author_nickname: string;
  title: string;
  body: string;
  upvote_count: number;
  downvote_count: number;
  comment_count: number;
  moderation_status: ModerationStatus;
  created_at: string;
}

export interface CommunityPostDetail extends CommunityPostOut {
  comments: CommentOut[];
}

export interface NewsPostOut {
  id: number;
  kind: "news_post";
  title: string;
  source_url: string;
  source_name: string | null;
  category: string | null;
  thumbnail_url: string | null;
  region: string | null;
  tags: string[];
  fake_news_risk_label: string | null;
  published_at: string | null;
  upvote_count: number;
  downvote_count: number;
  comment_count: number;
  moderation_status: ModerationStatus;
  created_at: string;
}

export interface NewsPostDetail extends NewsPostOut {
  body_text: string | null;
  comments: CommentOut[];
}

export interface FeedPage<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface VoteResult {
  upvote_count: number;
  downvote_count: number;
  user_vote: 1 | -1 | 0;
}

export interface ReportOut {
  id: number;
  target_type: "post" | "news_post" | "comment";
  target_id: number;
  reason: string;
  detail: string | null;
  status: string;
  created_at: string;
}

export interface ReportQueueItem extends ReportOut {
  target_preview: string;
}

export interface NewsSummaryOut {
  news_post_id: number;
  summary: string;
  model_name: string;
}

/** 커뮤니티/뉴스 게시글을 프론트에서 하나의 카드/상세 UI로 다루기 위한 정규화 타입. */
export interface FeedItem {
  id: number;
  kind: "community" | "news";
  boardOrCategoryLabel: string;
  title: string;
  bodyPreview: string;
  authorLabel: string;
  sourceUrl?: string;
  fakeNewsRiskLabel?: string | null;
  upvoteCount: number;
  downvoteCount: number;
  commentCount: number;
  createdAt: string;
}

export function communityPostToFeedItem(p: CommunityPostOut): FeedItem {
  return {
    id: p.id,
    kind: "community",
    boardOrCategoryLabel: p.board_slug,
    title: p.title,
    bodyPreview: p.body,
    authorLabel: p.author_nickname,
    upvoteCount: p.upvote_count,
    downvoteCount: p.downvote_count,
    commentCount: p.comment_count,
    createdAt: p.created_at,
  };
}

export function newsPostToFeedItem(n: NewsPostOut): FeedItem {
  return {
    id: n.id,
    kind: "news",
    boardOrCategoryLabel: n.category ?? "뉴스",
    title: n.title,
    bodyPreview: n.source_name ?? n.source_url,
    authorLabel: n.source_name ?? "출처 미상",
    sourceUrl: n.source_url,
    fakeNewsRiskLabel: n.fake_news_risk_label,
    upvoteCount: n.upvote_count,
    downvoteCount: n.downvote_count,
    commentCount: n.comment_count,
    createdAt: n.created_at,
  };
}
