/**
 * AuthContext – manages JWT token + current-user state across the app.
 *
 * Exposes:
 *   user          – the logged-in user object (or null)
 *   token         – raw JWT string (or null)
 *   login(...)    – call the /api/auth/login endpoint and persist state
 *   logout()      – clear state + redirect to /admin/login
 *   updateUser()  – update local state after a profile edit
 *   isAdmin       – convenience boolean derived from user.role
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface AuthUser {
  id: string;
  employee_number: string;
  name: string;
  email: string;
  phone?: string;
  company?: string;
  location?: string;
  avatar_color?: string;
  role: 'Admin' | 'HR';
  is_active: number;
  force_reset: number;
  created_at: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAdmin: boolean;
  login: (employeeNumber: string, password: string, rememberMe?: boolean) => Promise<void>;
  logout: () => void;
  updateUser: (updated: Partial<AuthUser>) => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEY_TOKEN = 'veridian_token';
const STORAGE_KEY_USER = 'veridian_user';
// Marker persisted in localStorage so we know which storage to read from on reload
const STORAGE_KEY_REMEMBER = 'veridian_remember';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // On mount, prefer sessionStorage. If the user had checked "Remember me",
  // the marker is in localStorage and the token is there too.
  const isRemembered = localStorage.getItem(STORAGE_KEY_REMEMBER) === 'true';
  const [token, setToken] = useState<string | null>(() =>
    isRemembered
      ? localStorage.getItem(STORAGE_KEY_TOKEN)
      : sessionStorage.getItem(STORAGE_KEY_TOKEN)
  );
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = isRemembered
      ? localStorage.getItem(STORAGE_KEY_USER)
      : sessionStorage.getItem(STORAGE_KEY_USER);
    return raw ? JSON.parse(raw) : null;
  });
  const [isLoading, setIsLoading] = useState(false);

  const isAdmin = user?.role === 'Admin';

  const login = useCallback(async (employeeNumber: string, password: string, rememberMe = false) => {
    setIsLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', employeeNumber);
      formData.append('password', password);

      let API_URL = import.meta.env.VITE_API_URL || '';
      // SAFETY FILTER: If we are not on localhost, force the URL to be https
      if (API_URL && !API_URL.includes('127.0.0.1') && !API_URL.includes('localhost')) {
        API_URL = API_URL.replace('http://', 'https://');
      }
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });

      if (!res.ok) {
        let detail = 'Login failed. Please try again.';
        try {
          const err = await res.json();
          detail = err.detail || detail;
        } catch {
          // Response body was empty (e.g. server unreachable / network error)
          detail = res.status === 0 ? 'Server not reachable. Is the backend running?' : `Server error (${res.status})`;
        }
        throw new Error(detail);
      }

      const data = await res.json();
      setToken(data.access_token);
      setUser(data.user);
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem(STORAGE_KEY_TOKEN, data.access_token);
      storage.setItem(STORAGE_KEY_USER, JSON.stringify(data.user));
      // Persist the preference so we know which storage to read from on reload
      if (rememberMe) {
        localStorage.setItem(STORAGE_KEY_REMEMBER, 'true');
      } else {
        localStorage.removeItem(STORAGE_KEY_REMEMBER);
      }

      // We no longer return or process forceReset since the flow is removed
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    // Always clear both storages + the remember flag on logout
    sessionStorage.removeItem(STORAGE_KEY_TOKEN);
    sessionStorage.removeItem(STORAGE_KEY_USER);
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_USER);
    localStorage.removeItem(STORAGE_KEY_REMEMBER);
    window.location.href = '/admin/login';
  }, []);

  const updateUser = useCallback((updated: Partial<AuthUser>) => {
    setUser(prev => {
      if (!prev) return prev;
      const next = { ...prev, ...updated };
      // Write back to whichever storage is active for this session
      const storage = localStorage.getItem(STORAGE_KEY_REMEMBER) === 'true' ? localStorage : sessionStorage;
      storage.setItem(STORAGE_KEY_USER, JSON.stringify(next));
      return next;
    });
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isAdmin, login, logout, updateUser, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
