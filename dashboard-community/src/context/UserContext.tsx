import { createContext, useContext, useState, type ReactNode } from "react";
import { getStoredUserId, setStoredUserId } from "../api/client";
import { registerUser } from "../api/community";
import type { CurrentUser } from "../api/types";

interface UserContextValue {
  user: CurrentUser | null;
  register: (nickname: string, regionSlug?: string) => Promise<void>;
  logout: () => void;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

/**
 * 임시 인증. TODO: replace with real OAuth2/JWT auth.
 * 새로고침 시 서버에 저장된 프로필을 다시 불러오지 않는다 — user_id만 localStorage에
 * 남아있고 닉네임 등은 세션 동안만 메모리에 유지된다 (재로그인 없이 새로고침하면
 * X-User-Id는 유지되지만 화면 상단 닉네임 표시는 다시 등록해야 나타남 — MVP 한계).
 */
export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);

  async function register(nickname: string, regionSlug?: string) {
    const created = await registerUser(nickname, regionSlug);
    setStoredUserId(created.id);
    setUser(created);
  }

  function logout() {
    setStoredUserId(null);
    setUser(null);
  }

  return <UserContext.Provider value={{ user, register, logout }}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}

export function hasStoredSession(): boolean {
  return getStoredUserId() !== null;
}
