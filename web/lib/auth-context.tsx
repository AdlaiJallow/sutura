"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, getAccessToken, setAccessToken } from "./api";
import type { UserProfile } from "./types";

export type AuthStatus = "checking" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  /** Best-effort profile fetched once authenticated; null while loading or if the
   * fetch fails (never blocks the auth gate — only affects the profile chip). */
  user: UserProfile | null;
  /** Called by the login page right after `POST /auth/login` succeeds, so the app
   * knows it's authenticated immediately — no silent-refresh loading flash on the
   * very next page. */
  login: (accessToken: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Re-fetches `GET /users/me` so a profile edit on the Settings page (name,
   * currency) is reflected immediately wherever `user` is read — e.g. the
   * header's initials chip — without waiting for a full reload. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * D-026: there is no persisted "is logged in" flag. This provider IS the
 * source of truth for the session, for as long as the tab is open:
 *   - On mount, if an access token is already in memory (e.g. `login()` just ran),
 *     trust it immediately — no network round trip, no loading flash.
 *   - Otherwise, attempt a silent `POST /auth/refresh` (the httpOnly refresh
 *     cookie goes automatically). Success -> authenticated with a fresh access
 *     token. Failure (401/network) -> unauthenticated.
 * `app/(app)/layout.tsx` reads `status` to gate every protected route.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<UserProfile | null>(null);
  const hasCheckedRef = useRef(false);

  const loadUser = useCallback(async () => {
    try {
      const profile = await api.users.me();
      setUser(profile);
    } catch {
      // Non-fatal: the profile chip falls back to a generic state. Auth status
      // itself is not affected by this call.
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (hasCheckedRef.current) return;
    hasCheckedRef.current = true;

    void (async () => {
      if (getAccessToken()) {
        setStatus("authenticated");
        await loadUser();
        return;
      }

      try {
        const { access_token } = await api.auth.refresh();
        setAccessToken(access_token);
        setStatus("authenticated");
        await loadUser();
      } catch {
        setAccessToken(null);
        setStatus("unauthenticated");
      }
    })();
  }, [loadUser]);

  const login = useCallback(
    async (token: string) => {
      setAccessToken(token);
      setStatus("authenticated");
      await loadUser();
    },
    [loadUser],
  );

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      // Best-effort — clear local session state regardless of server response
      // (e.g. the cookie was already expired/revoked).
    }
    setAccessToken(null);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, logout, refreshUser: loadUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
