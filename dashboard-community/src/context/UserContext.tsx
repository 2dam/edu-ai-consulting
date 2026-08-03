import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getStoredAccessToken, setStoredAccessToken } from "../api/client";
import { getCurrentUser, loginUser, logoutUser, registerUser } from "../api/community";
import type { CurrentUser } from "../api/types";

interface UserContextValue {
  user: CurrentUser | null;
  loading: boolean;
  register: (nickname: string, password: string, regionSlug?: string) => Promise<void>;
  login: (nickname: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(getStoredAccessToken() !== null);

  useEffect(() => {
    if (!getStoredAccessToken()) return;
    getCurrentUser()
      .then(setUser)
      .catch(() => setStoredAccessToken(null))
      .finally(() => setLoading(false));
  }, []);

  async function register(nickname: string, password: string, regionSlug?: string) {
    const auth = await registerUser(nickname, password, regionSlug);
    setStoredAccessToken(auth.access_token);
    setUser(auth.user);
  }

  async function login(nickname: string, password: string) {
    const auth = await loginUser(nickname, password);
    setStoredAccessToken(auth.access_token);
    setUser(auth.user);
  }

  async function logout() {
    try { await logoutUser(); } catch { /* clear local session even if API is unavailable */ }
    setStoredAccessToken(null);
    setUser(null);
  }

  return <UserContext.Provider value={{ user, loading, register, login, logout }}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}

export function hasStoredSession(): boolean {
  return getStoredAccessToken() !== null;
}
