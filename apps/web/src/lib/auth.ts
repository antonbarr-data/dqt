const TOKEN_KEY = "dqt_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface TokenPayload {
  sub: string;
  email: string;
  role: string;
  tenant: string;
  exp: number;
}

export function decodeToken(token: string): TokenPayload | null {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload)) as TokenPayload;
  } catch {
    return null;
  }
}

export function isSysAdmin(): boolean {
  const token = getToken();
  if (!token) return false;
  const payload = decodeToken(token);
  return payload?.role === "sysadmin";
}
