/**
 * ModelForge Authentication Service
 * Integrates with Supabase Auth when VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are provided.
 * Provides configuration status checks and clean session handling.
 */

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(
  SUPABASE_URL && 
  SUPABASE_ANON_KEY && 
  !SUPABASE_URL.includes('your-supabase') && 
  !SUPABASE_ANON_KEY.includes('your-anon-key')
);

export const supabase = isSupabaseConfigured
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

const LOCAL_STORAGE_SESSION_KEY = 'modelforge_auth_session';

/**
 * Get current session from Supabase or verified local store
 */
export async function getSession() {
  if (supabase) {
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      console.warn('Supabase getSession error:', error.message);
      return null;
    }
    return data.session;
  }

  // Fallback to local storage session if Supabase is in dev/configured mode
  try {
    const saved = localStorage.getItem(LOCAL_STORAGE_SESSION_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed && parsed.user) {
        return parsed;
      }
    }
  } catch (err) {
    console.warn('Error reading saved auth session:', err);
  }

  return null;
}

/**
 * Sign in user with email and password
 */
export async function signIn({ email, password, rememberMe: _rememberMe = true }) {
  if (!email || !password) {
    throw new Error('Please enter both email and password.');
  }

  if (supabase) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });

    if (error) {
      throw new Error(error.message || 'Invalid email or password.');
    }

    if (data?.session) {
      localStorage.setItem(LOCAL_STORAGE_SESSION_KEY, JSON.stringify(data.session));
    }

    return data;
  }

  // If Supabase is not configured:
  // Check if developer mode allows a pre-configured local workspace user for testing
  const allowDevAuth = import.meta.env.VITE_ENABLE_DEV_AUTH === 'true';
  if (allowDevAuth) {
    // Verified development demo session
    const devSession = {
      access_token: 'modelforge-dev-token-' + Date.now(),
      token_type: 'bearer',
      user: {
        id: 'usr_dev_workspace_lead',
        email: email.trim(),
        user_metadata: {
          name: email.split('@')[0],
        },
      },
      expires_at: Math.floor(Date.now() / 1000) + 86400 * 7,
    };
    localStorage.setItem(LOCAL_STORAGE_SESSION_KEY, JSON.stringify(devSession));
    return { user: devSession.user, session: devSession };
  }

  throw new Error(
    'Supabase Auth is not configured. Please add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your frontend/.env file.'
  );
}

/**
 * Sign up user with email, password, and metadata
 */
export async function signUp({ email, password, name = '' }) {
  if (!email || !password) {
    throw new Error('Please provide email and password.');
  }

  if (password.length < 8) {
    throw new Error('Password must be at least 8 characters long.');
  }

  if (supabase) {
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: {
          name: name.trim(),
          workspace: 'My Workspace',
        },
      },
    });

    if (error) {
      throw new Error(error.message || 'Failed to create account.');
    }

    if (data?.session) {
      localStorage.setItem(LOCAL_STORAGE_SESSION_KEY, JSON.stringify(data.session));
    }

    return data;
  }

  const allowDevAuth = import.meta.env.VITE_ENABLE_DEV_AUTH === 'true';
  if (allowDevAuth) {
    const devSession = {
      access_token: 'modelforge-dev-token-' + Date.now(),
      token_type: 'bearer',
      user: {
        id: 'usr_dev_' + Math.random().toString(36).substring(2, 9),
        email: email.trim(),
        user_metadata: {
          name: name.trim() || email.split('@')[0],
        },
      },
      expires_at: Math.floor(Date.now() / 1000) + 86400 * 7,
    };
    localStorage.setItem(LOCAL_STORAGE_SESSION_KEY, JSON.stringify(devSession));
    return { user: devSession.user, session: devSession };
  }

  throw new Error(
    'Supabase Auth is not configured. Please add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your frontend/.env file.'
  );
}

/**
 * Send password reset email
 */
export async function resetPassword(email) {
  if (!email || !email.trim()) {
    throw new Error('Please enter your email address.');
  }

  if (supabase) {
    const { data, error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/login`,
    });

    if (error) {
      throw new Error(error.message || 'Failed to send password reset email.');
    }

    return data;
  }

  throw new Error(
    'Password recovery requires Supabase Auth configuration. Please configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.'
  );
}

/**
 * Sign out user and clear stored session
 */
export async function signOut() {
  if (supabase) {
    await supabase.auth.signOut().catch(() => {});
  }
  localStorage.removeItem(LOCAL_STORAGE_SESSION_KEY);
}

/**
 * Subscribe to Auth State changes
 */
export function onAuthStateChange(callback) {
  if (supabase) {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (session) {
          localStorage.setItem(LOCAL_STORAGE_SESSION_KEY, JSON.stringify(session));
        } else {
          localStorage.removeItem(LOCAL_STORAGE_SESSION_KEY);
        }
        callback(session?.user || null, session);
      }
    );
    return () => subscription?.unsubscribe();
  }

  // Non-Supabase listener
  const checkStorage = () => {
    getSession().then((session) => {
      callback(session?.user || null, session);
    });
  };

  window.addEventListener('storage', checkStorage);
  return () => window.removeEventListener('storage', checkStorage);
}

export default {
  isSupabaseConfigured,
  supabase,
  getSession,
  signIn,
  signUp,
  resetPassword,
  signOut,
  onAuthStateChange,
};
