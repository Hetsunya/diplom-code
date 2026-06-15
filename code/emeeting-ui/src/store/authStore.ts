// src/store/authStore.ts
import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  user: { email: string } | null;
  setAuth: (user: { email: string } | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: (() => {
    try {
      return sessionStorage.getItem("auth_email") != null;
    } catch {
      return false;
    }
  })(),
  user: (() => {
    try {
      const email = sessionStorage.getItem("auth_email");
      return email ? { email } : null;
    } catch {
      return null;
    }
  })(),
  setAuth: (user) => {
    try {
      if (user?.email) sessionStorage.setItem("auth_email", user.email);
      else sessionStorage.removeItem("auth_email");
    } catch {
      // ignore
    }
    set({ user, isAuthenticated: !!user });
  },
}));