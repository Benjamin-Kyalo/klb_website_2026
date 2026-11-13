import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { auth } from "../lib/api.js";
import { can as canPermission, effectivePermissions, ROLE_LABELS } from "../lib/permissions.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Idle timeout: sign out after 25 minutes without interaction. This mirrors
  // the backend session lifetime (30 minutes) and is slightly shorter so the
  // client logs out cleanly before the server session expires.
  const IDLE_TIMEOUT_MS = 25 * 60 * 1000;

  const refresh = useCallback(async () => {
    try {
      const data = await auth.me();
      setUser(data.user);
      return data.user;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email, password) => {
    const data = await auth.login(email, password);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await auth.logout();
    } finally {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    let timer = null;
    const reset = () => {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        logout();
      }, IDLE_TIMEOUT_MS);
    };
    const events = ["mousemove", "keydown", "click", "scroll", "touchstart"];
    events.forEach((event) =>
      window.addEventListener(event, reset, { passive: true })
    );
    reset();
    return () => {
      if (timer) window.clearTimeout(timer);
      events.forEach((event) => window.removeEventListener(event, reset));
    };
  }, [user, logout]);

  const value = useMemo(() => {
    const permissions = effectivePermissions(user);
    return {
      user,
      loading,
      login,
      logout,
      refresh,
      permissions,
      can: (module, action = "view") => canPermission(user, module, action),
      isAuthenticated: Boolean(user),
      isSuperAdministrator: Boolean(user?.is_super_administrator || user?.role === "super_admin"),
      isAdministrator: Boolean(user?.is_administrator),
      isEditor: Boolean(user),
      roleLabel: user ? user.role_label || ROLE_LABELS[user.role] || user.role : "",
    };
  }, [user, loading, login, logout, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
