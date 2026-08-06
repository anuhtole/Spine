import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { authLogin, authLogout, authMe, type UserInfo } from "@/api/client";

interface AuthState {
  ready: boolean;
  user: UserInfo | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);

  const refresh = useCallback(async () => {
    try {
      const me = await authMe();
      setUser(me.authenticated && me.user ? me.user : null);
    } catch {
      setUser(null);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authLogin(email, password);
    setUser(res.user);
  }, []);

  const logout = useCallback(async () => {
    await authLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ ready, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
