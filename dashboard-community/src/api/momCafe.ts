import { api } from "./client";
import type { BoardOut, CommunityPostOut, FeedPage } from "./types";

export function getBoards(): Promise<BoardOut[]> {
  return api.get<BoardOut[]>("/mom-cafe/boards");
}

export function getRegionBoard(regionSlug: string, limit = 20, offset = 0): Promise<FeedPage<CommunityPostOut>> {
  return api.get<FeedPage<CommunityPostOut>>(`/mom-cafe/region/${regionSlug}?limit=${limit}&offset=${offset}`);
}

export function getEducationBoard(limit = 20, offset = 0): Promise<FeedPage<CommunityPostOut>> {
  return api.get<FeedPage<CommunityPostOut>>(`/mom-cafe/education?limit=${limit}&offset=${offset}`);
}

export function getParentingBoard(limit = 20, offset = 0): Promise<FeedPage<CommunityPostOut>> {
  return api.get<FeedPage<CommunityPostOut>>(`/mom-cafe/parenting?limit=${limit}&offset=${offset}`);
}
