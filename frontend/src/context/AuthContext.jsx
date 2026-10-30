import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  getSession,
  signIn,
  signUp,
  resetPassword as apiResetPassword,
  signOut,
  onAuthStateChange,
  isSupabaseConfigured,
} from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    // Load initial session
    getSession()
      .then((sess) => {
        if (!mounted) return;
        setSession(sess);
        setUser(sess?.user || null);
        setLoading(false);
      })
      .catch((err) => {
        console.warn('Initial session check error:', err);
        if (!mounted) return;
        setLoading(false);
      });

    const unsubscribe = onAuthStateChange((newUser, newSession) => {
      if (!mounted) return;
      setUser(newUser);
      setSession(newSession);
      setLoading(false);
    });

    return () => {
      mounted = false;
      if (typeof unsubscribe === 'function') unsubscribe();
    };
  }, []);

  const login = async (credentials) => {
    const res = await signIn(credentials);
    setUser(res.user);
    setSession(res.session);
    return res;
  };

  const register = async (details) => {
    const res = await signUp(details);
    setUser(res.user);
    setSession(res.session);
    return res;
  };

  const logout = async () => {
    await signOut();
    setUser(null);
    setSession(null);
  };

  const recoverPassword = async (email) => {
    return await apiResetPassword(email);
  };

  const value = {
    user,
    session,
    isAuthenticated: Boolean(user),
    loading,
    isSupabaseConfigured,
    login,
    register,
    logout,
    resetPassword: recoverPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

