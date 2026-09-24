import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import * as auth from '../services/auth';
import type { LocalAccount } from '../services/auth';

interface AuthContextValue {
  account: LocalAccount | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<LocalAccount>;
  signOut: () => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<LocalAccount>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<LocalAccount | null>(() => auth.getSession());

  // Verify and refresh session on mount
  useEffect(() => {
    auth.getCurrentUser().then(user => {
      if (user) {
        setAccount(user);
      } else if (!auth.getToken()) {
        setAccount(null);
      }
    });
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const next = await auth.login(email, password);
    setAccount(next);
    return next;
  }, []);

  const signOut = useCallback(async () => {
    await auth.logout();
    setAccount(null);
  }, []);

  const signUp = useCallback(async (name: string, email: string, password: string) => {
    return await auth.createAccount(name, email, password);
  }, []);

  const value = useMemo(() => ({
    account,
    isAuthenticated: !!account,
    signIn,
    signOut,
    signUp,
  }), [account, signIn, signOut, signUp]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within AuthProvider');
  return value;
}
