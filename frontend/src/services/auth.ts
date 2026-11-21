/**
 * Real Backend Authentication & User Management Service for AcadAssist.
 * Connects directly to FastAPI endpoints:
 * - POST  /api/auth/register
 * - POST  /api/auth/login
 * - GET   /api/auth/me
 * - PATCH /api/auth/profile
 * - POST  /api/auth/change-password
 * - POST  /api/auth/forgot-password
 * - POST  /api/auth/reset-password
 * - GET   /api/auth/workspace-state
 * - PUT   /api/auth/workspace-state
 * - POST  /api/auth/logout
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

function emitAuthChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('acadassist:auth-changed'));
  }
}

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
    emitAuthChanged();
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

function mapUserPayload(u: AuthResponse['user']): LocalAccount {
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    role: u.role,
    academicLevel: u.academic_level,
    fieldOfStudy: u.field_of_study,
    bio: u.bio,
    createdAt: u.created_at,
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
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = (await res.json()) as AuthResponse;
  setToken(data.access_token);
  const account = mapUserPayload(data.user);
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
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = (await res.json()) as AuthResponse;
  setToken(data.access_token);
  const account = mapUserPayload(data.user);
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
        await logout();
      }
      return null;
    }
    const data = await res.json();
    const account = mapUserPayload(data);
    setCachedUser(account);
    return account;
  } catch {
    return getCachedUser();
  }
}

export async function updateProfile(patch: {
  name?: string;
  email?: string;
  role?: string;
  academicLevel?: string;
  fieldOfStudy?: string;
  bio?: string;
}): Promise<LocalAccount | null> {
  const token = getToken();
  if (!token) return null;

  const url = API_BASE ? `${API_BASE}/api/auth/profile` : '/api/auth/profile';
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      name: patch.name,
      email: patch.email,
      role: patch.role,
      academic_level: patch.academicLevel,
      field_of_study: patch.fieldOfStudy,
      bio: patch.bio,
    }),
  });

  if (!res.ok) {
    let errorDetail = 'Failed to update profile.';
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = await res.json();
  const updated = mapUserPayload(data);
  setCachedUser(updated);
  return updated;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<string> {
  const token = getToken();
  if (!token) throw new Error('You must be signed in to change your password.');

  const url = API_BASE ? `${API_BASE}/api/auth/change-password` : '/api/auth/change-password';
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  if (!res.ok) {
    let errorDetail = 'Unable to change password.';
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = await res.json();
  return data.message || 'Password changed successfully.';
}

export async function requestPasswordReset(email: string): Promise<{
  message: string;
  resetToken?: string;
  expiresInMinutes: number;
}> {
  const url = API_BASE ? `${API_BASE}/api/auth/forgot-password` : '/api/auth/forgot-password';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.trim().toLowerCase() }),
  });

  if (!res.ok) {
    let errorDetail = 'Unable to initiate password recovery.';
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = await res.json();
  return {
    message: data.message || 'Password reset token generated.',
    resetToken: data.reset_token,
    expiresInMinutes: data.expires_in_minutes || 15,
  };
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<string> {
  const url = API_BASE ? `${API_BASE}/api/auth/reset-password` : '/api/auth/reset-password';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token: token.trim(),
      new_password: newPassword,
    }),
  });

  if (!res.ok) {
    let errorDetail = 'Unable to reset password.';
    try {
      const err = await res.json();
      if (err.detail) errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(errorDetail);
  }

  const data = await res.json();
  return data.message || 'Password reset successfully.';
}

export async function fetchWorkspaceState(): Promise<{
  enrolled_courses: string[] | null;
  course_progress: Record<string, any>;
  course_preferences: string[];
  events: any[];
  study_goals: any[];
  profile_extra: Record<string, any>;
} | null> {
  const token = getToken();
  if (!token) return null;

  const url = API_BASE ? `${API_BASE}/api/auth/workspace-state` : '/api/auth/workspace-state';
  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function persistWorkspaceState(payload: {
  enrolled_courses?: string[];
  course_progress?: Record<string, any>;
  course_preferences?: string[];
  events?: any[];
  study_goals?: any[];
  profile_extra?: Record<string, any>;
}): Promise<void> {
  const token = getToken();
  if (!token) return;

  const url = API_BASE ? `${API_BASE}/api/auth/workspace-state` : '/api/auth/workspace-state';
  try {
    await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
  } catch {
    /* offline fallback stays in localStorage */
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
