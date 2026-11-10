import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { auth } from "../lib/api.js";
import { can as canPermission, effectivePermissions, ROLE_LABELS } from "../lib/permissions.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

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
