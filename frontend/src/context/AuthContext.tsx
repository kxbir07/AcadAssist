import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import * as auth from '../services/auth';
import type { LocalAccount } from '../services/auth';

interface AuthContextValue {
  account: LocalAccount | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<LocalAccount>;
  signOut: () => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<LocalAccount>;
  refreshAccount: () => Promise<LocalAccount | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<LocalAccount | null>(() => auth.getSession());

  const refreshAccount = useCallback(async () => {
    const user = await auth.getCurrentUser();
    if (user) {
      setAccount(user);
      return user;
    }
    if (!auth.getToken()) {
      setAccount(null);
    }
    return null;
  }, []);

  // Verify and refresh session on mount and listen to auth changes
  useEffect(() => {
    refreshAccount();
    const onAuthChange = () => {
      setAccount(auth.getSession());
    };
    window.addEventListener('acadassist:auth-changed', onAuthChange);
    return () => window.removeEventListener('acadassist:auth-changed', onAuthChange);
  }, [refreshAccount]);

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
    const created = await auth.createAccount(name, email, password);
    setAccount(created);
    return created;
  }, []);

  const value = useMemo(() => ({
    account,
    isAuthenticated: !!account && !!auth.getToken(),
    signIn,
    signOut,
    signUp,
    refreshAccount,
  }), [account, signIn, signOut, signUp, refreshAccount]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within AuthProvider');
  return value;
}
