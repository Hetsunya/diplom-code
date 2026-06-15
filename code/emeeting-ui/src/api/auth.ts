// src/api/auth.ts
import { apiFetch } from './http';

export async function login(email: string, password: string) {
  const res = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error('Login failed');
  return res.json();
}

export async function logout() {
  const res = await apiFetch('/auth/logout', { method: 'POST' });
  if (!res.ok) throw new Error('Logout failed');
}