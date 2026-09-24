/**
 * Real Backend Authentication Service for AcadAssist.
 * Connects directly to FastAPI endpoints:
 * - POST /api/auth/register
 * - POST /api/auth/login
 * - GET  /api/auth/me
 * - POST /api/auth/logout
 */

export interface LocalAccount {
  id: string;
  name: string;
  email: string;
  role?: string;
  academicLevel?: string;
  fieldOfStudy?: string;
  bio?: string;
  createdAt?: string;
}

const TOKEN_KEY = 'acadassist.auth.token';
const USER_KEY = 'acadassist.auth.user';

const API_BASE = import.meta.env.VITE_API_URL?.replace(/\/$/, '') || '';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    /* storage is optional */
  }
}

export function getCachedUser(): LocalAccount | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as LocalAccount) : null;
  } catch {
    return null;
  }
}

export function setCachedUser(user: LocalAccount | null) {
  try {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  } catch {
    /* storage is optional */
  }
}

export function getSession(): LocalAccount | null {
  return getCachedUser();
}

export function isAuthenticated(): boolean {
  return !!getToken() && !!getCachedUser();
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name: string;
    role?: string;
    academic_level?: string;
    field_of_study?: string;
    bio?: string;
    created_at?: string;
  };
}

export async function login(email: string, password: string): Promise<LocalAccount> {
  const url = API_BASE ? `${API_BASE}/api/auth/login` : '/api/auth/login';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });

  if (!res.ok) {
    let errorDetail = 'Incorrect email or password.';
    try {
      const err = await res.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = (await res.json()) as AuthResponse;
  setToken(data.access_token);

  const account: LocalAccount = {
    id: data.user.id,
    name: data.user.name,
    email: data.user.email,
    role: data.user.role,
    academicLevel: data.user.academic_level,
    fieldOfStudy: data.user.field_of_study,
    bio: data.user.bio,
    createdAt: data.user.created_at,
  };
  setCachedUser(account);
  return account;
}

export async function createAccount(name: string, email: string, password: string): Promise<LocalAccount> {
  const url = API_BASE ? `${API_BASE}/api/auth/register` : '/api/auth/register';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      name: name.trim(),
      password,
      field_of_study: 'Computer Science',
    }),
  });

  if (!res.ok) {
    let errorDetail = 'Unable to register account.';
    try {
      const err = await res.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = (await res.json()) as AuthResponse;
  setToken(data.access_token);

  const account: LocalAccount = {
    id: data.user.id,
    name: data.user.name,
    email: data.user.email,
    role: data.user.role,
    academicLevel: data.user.academic_level,
    fieldOfStudy: data.user.field_of_study,
    bio: data.user.bio,
    createdAt: data.user.created_at,
  };
  setCachedUser(account);
  return account;
}

export async function getCurrentUser(): Promise<LocalAccount | null> {
  const token = getToken();
  if (!token) return null;

  const url = API_BASE ? `${API_BASE}/api/auth/me` : '/api/auth/me';
  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      if (res.status === 401) {
        logout();
      }
      return null;
    }
    const data = await res.json();
    const account: LocalAccount = {
      id: data.id,
      name: data.name,
      email: data.email,
      role: data.role,
      academicLevel: data.academic_level,
      fieldOfStudy: data.field_of_study,
      bio: data.bio,
      createdAt: data.created_at,
    };
    setCachedUser(account);
    return account;
  } catch {
    return getCachedUser();
  }
}

export async function logout(): Promise<void> {
  const token = getToken();
  if (token) {
    try {
      const url = API_BASE ? `${API_BASE}/api/auth/logout` : '/api/auth/logout';
      await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      /* network error on logout can be ignored */
    }
  }
  setToken(null);
  setCachedUser(null);
}
