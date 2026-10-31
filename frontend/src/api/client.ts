/**
 * Axios API client for SanshthaSetu.
 *
 * - Base URL read from VITE_API_BASE_URL environment variable.
 * - Request interceptor: attaches "Authorization: Bearer <token>" to every
 *   request when a token is present in the auth store.
 * - Response interceptor: on 401, clears the stored token and redirects to
 *   /login. This covers expired tokens and revoked sessions.
 *
 * Usage:
 *   import apiClient from '@/api/client'
 *   const data = await apiClient.post('/auth/login', { email, password })
 */

import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// ---------------------------------------------------------------------------
// Instance
// ---------------------------------------------------------------------------

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL as string,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---------------------------------------------------------------------------
// Request interceptor — attach Bearer token
// ---------------------------------------------------------------------------

apiClient.interceptors.request.use(
  (config) => {
    // Read token directly from the store state (no React hook needed here).
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ---------------------------------------------------------------------------
// Response interceptor — handle 401 (expired / invalid token)
// ---------------------------------------------------------------------------

apiClient.interceptors.response.use(
  // Pass through successful responses unchanged.
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Don't intercept 401s on the login page itself — those are expected
      // credential errors that the LoginPage component handles directly.
      if (window.location.pathname !== '/login') {
        // Clear auth state so the UI resets to unauthenticated.
        useAuthStore.getState().clearAuth()
        // Hard redirect — forces a clean React tree remount at the login page.
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
