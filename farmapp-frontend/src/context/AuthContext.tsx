import { useState, useCallback, type ReactNode } from "react";
import type { User, LoginPayload, RegisterPayload } from "../types";
import { authApi } from "../api/authApi";
import { AuthContext, type AuthContextType } from "./authContext";

// Restore the session from localStorage (read once, on first render)
function readStoredSession(): { token: string | null; user: User | null } {
  const storedToken = localStorage.getItem("access_token");
  const storedUser = localStorage.getItem("user");
  if (storedToken && storedUser) {
    return { token: storedToken, user: JSON.parse(storedUser) as User };
  }
  return { token: null, user: null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readStoredSession().user);
  const [token, setToken] = useState<string | null>(() => readStoredSession().token);
  // Session restore is synchronous, so there is no loading phase
  const isLoading = false;

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await authApi.login(payload);
    localStorage.setItem("access_token", response.access_token);
    localStorage.setItem("user", JSON.stringify(response.user));
    setToken(response.access_token);
    setUser(response.user);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await authApi.register(payload);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Even if logout API fails, clear local state
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
  }, []);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
