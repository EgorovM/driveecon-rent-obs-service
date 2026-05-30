import { createContext, useContext, useState, type ReactNode } from "react";
import { apiJson, clearToken, getToken, setToken } from "./api";

type AuthState = {
  token: string | null;
  username: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(getToken());
  const [username, setUsername] = useState<string | null>(
    localStorage.getItem("drivee_user"),
  );

  async function login(user: string, password: string): Promise<void> {
    const res = await apiJson<{ token: string; username: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: user, password }),
    });
    setToken(res.token);
    localStorage.setItem("drivee_user", res.username);
    setTok(res.token);
    setUsername(res.username);
  }

  function logout(): void {
    clearToken();
    localStorage.removeItem("drivee_user");
    setTok(null);
    setUsername(null);
  }

  return (
    <AuthContext.Provider value={{ token, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth должен использоваться внутри AuthProvider");
  return ctx;
}
