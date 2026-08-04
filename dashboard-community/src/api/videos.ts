import { api } from "./client";
import type { AdmissionVideoOut, FeedPage } from "./types";

export function getAdmissionVideos(params: {
  q?: string;
  searchQuery?: string;
  limit?: number;
  offset?: number;
}): Promise<FeedPage<AdmissionVideoOut>> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.searchQuery) query.set("search_query", params.searchQuery);
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));
  return api.get<FeedPage<AdmissionVideoOut>>(`/videos/feed?${query.toString()}`);
}
