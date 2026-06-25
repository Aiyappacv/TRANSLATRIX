import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthSession, RoleCode, User } from "@/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  activeRole: RoleCode | null;
  setActiveRole: (role: RoleCode) => void;
  updateTokens: (accessToken: string, refreshToken?: string) => void;
  setSession: (session: AuthSession) => void;
  clearSession: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      activeRole: null,
      setActiveRole: (role) => {
        const user = get().user;
        if (user?.roles.includes(role)) set({ activeRole: role });
      },
      updateTokens: (accessToken, refreshToken) => set((state) => ({ accessToken, refreshToken: refreshToken ?? state.refreshToken })),
      setSession: (session) => set({ user: session.user, accessToken: session.accessToken, refreshToken: session.refreshToken, activeRole: session.user.roles[0] ?? null }),
      clearSession: () => set({ user: null, accessToken: null, refreshToken: null, activeRole: null }),
      isAuthenticated: () => Boolean(get().user && get().accessToken),
    }),
    { name: "translatrix-auth-production" },
  ),
);
