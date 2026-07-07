import { api } from "./client";
import type { ModerationStatus, ReportQueueItem } from "./types";

export function getReportQueue(status: string = "open"): Promise<ReportQueueItem[]> {
  return api.get<ReportQueueItem[]>(`/admin/community/reports?status=${status}`);
}

export function moderateCommunityPost(
  postId: number,
  moderationStatus: ModerationStatus,
  reason?: string,
  relatedReportId?: number
): Promise<{ id: number; moderation_status: ModerationStatus }> {
  return api.patch(`/admin/community/posts/${postId}/moderation`, {
    moderation_status: moderationStatus,
    reason: reason || null,
    related_report_id: relatedReportId ?? null,
  });
}

export function moderateNewsPost(
  newsId: number,
  moderationStatus: ModerationStatus,
  reason?: string,
  relatedReportId?: number
): Promise<{ id: number; moderation_status: ModerationStatus }> {
  return api.patch(`/admin/news/posts/${newsId}/moderation`, {
    moderation_status: moderationStatus,
    reason: reason || null,
    related_report_id: relatedReportId ?? null,
  });
}
