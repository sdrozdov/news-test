import { useCallback, useEffect, useState } from "react";

import { ApiError, api, errorMessage } from "../api/client";
import type { User } from "../types";

/**
 * Resolves the current user from the session cookie. A 401 means "not signed in"
 * (show the sign-in gate); in local dev mode the backend returns a stub user, so
 * the app opens straight to the feed without WorkOS.
 */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // A failed WorkOS callback redirects back with ?auth_error; surface it once and
  // strip just that flag (preserving any other params). Done in an effect, not a
  // state initializer, so the side effect isn't lost under StrictMode.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("auth_error")) {
      params.delete("auth_error");
      const rest = params.toString();
      window.history.replaceState({}, "", window.location.pathname + (rest ? `?${rest}` : ""));
      setError("Sign-in failed — please try again.");
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const me = await api.me();
        if (active) setUser(me);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          if (active) setUser(null);
        } else if (active) {
          // Don't clobber a sign-in-failure message already shown above.
          setError((prev) => prev ?? errorMessage(err, "Could not reach the server."));
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback((screenHint?: "sign-in" | "sign-up") => {
    window.location.href = api.loginUrl(screenHint);
  }, []);

  const logout = useCallback(async () => {
    try {
      const { logout_url } = await api.logout();
      window.location.href = logout_url;
    } catch {
      window.location.reload();
    }
  }, []);

  return { user, loading, error, login, logout };
}
