
import { createContext, useContext } from "react";
import type { CurrentUser } from "../api/types";

export interface UserContextValue {
  user: CurrentUser | null;
  loading: boolean;
  register: (nickname: string, password: string, regionSlug?: string) => Promise<void>;
  login: (nickname: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const UserContext = createContext<UserContextValue | undefined>(undefined);

export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) throw new Error("useUser must be used within UserProvider");
  return context;
}
