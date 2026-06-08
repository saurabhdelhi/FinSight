'use client';

/**
 * Auth context provider — manages JWT tokens and user state.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api from '@/lib/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id: string;
  org_name: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; org_name: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('finsight_token');
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const userData = await api.getMe();
      setUser(userData);
    } catch {
      localStorage.removeItem('finsight_token');
      localStorage.removeItem('finsight_refresh_token');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    localStorage.setItem('finsight_token', tokens.access_token);
    localStorage.setItem('finsight_refresh_token', tokens.refresh_token);
    await loadUser();
  };

  const register = async (data: { email: string; password: string; full_name: string; org_name: string }) => {
    const tokens = await api.register(data);
    localStorage.setItem('finsight_token', tokens.access_token);
    localStorage.setItem('finsight_refresh_token', tokens.refresh_token);
    await loadUser();
  };

  const logout = () => {
    localStorage.removeItem('finsight_token');
    localStorage.removeItem('finsight_refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
