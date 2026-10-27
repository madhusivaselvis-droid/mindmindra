const API_URL = import.meta.env.VITE_API_URL || '';
const TOKEN_KEY = 'mindner-session-token';

export function csrfHeaders(): Record<string, string> {
  const value = document.cookie.split('; ').find(item => item.startsWith('mindner_csrf='))?.split('=')[1];
  return value ? {'X-CSRF-Token': decodeURIComponent(value)} : {};
}

export type AuthUser = { id: string; name: string; email: string; role: string };

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function safeJson(response: Response): Promise<Record<string, string>> {
  try { return await response.json(); } catch { return {}; }
}

export async function authenticate(path: '/auth/login' | '/auth/register', body: Record<string, string>): Promise<AuthUser> {
  const response = await fetch(`${API_URL}${path}`, { method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json', ...csrfHeaders()}, body: JSON.stringify(body) });
  if (!response.ok) throw new Error((await safeJson(response)).detail || 'Unable to authenticate');
  return getMe();
}

export async function getMe(): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/auth/me`, { credentials: 'include' });
  if (!response.ok) throw new Error('Session expired');
  return response.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {method: 'POST', credentials: 'include', headers: csrfHeaders()});
  clearToken();
}
