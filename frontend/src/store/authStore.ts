/**
 * Auth state — Zustand store persisted to localStorage.
 *
 * Persisted under the key "sanshthasetu-auth" so a page refresh
 * restores the session without a new login.
 *
 * clearAuth() is called by:
 *   - The logout button in portal layouts (Task 16)
 *   - The Axios 401 response interceptor in client.ts (this task)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthState {
  token: string | null
  role: string | null
  userId: string | null
  email: string | null

  /** Store credentials after a successful login. */
  setAuth: (token: string, role: string, userId: string, email: string) => void

  /** Clear all credentials (logout / 401 intercept). */
  clearAuth: () => void

  /** Convenience: true when a token is present. */
  isAuthenticated: () => boolean
}

// ---------------------------------------------------------------------------
// Role → portal path mapping (shared with ProtectedRoute and login redirect)
// ---------------------------------------------------------------------------

export const ROLE_PORTAL: Record<string, string> = {
  college_admin: '/college',
  main_admin: '/admin',
  regional_officer: '/admin',
  bureau_officer: '/admin',
  competent_authority: '/admin',
  evc_member: '/evc',
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      role: null,
      userId: null,
      email: null,

      setAuth: (token, role, userId, email) =>
        set({ token, role, userId, email }),

      clearAuth: () =>
        set({ token: null, role: null, userId: null, email: null }),

      isAuthenticated: () => get().token !== null,
    }),
    {
      name: 'sanshthasetu-auth', // localStorage key
      // Only persist the data fields — not the action functions.
      partialize: (state) => ({
        token: state.token,
        role: state.role,
        userId: state.userId,
        email: state.email,
      }),
    },
  ),
)
