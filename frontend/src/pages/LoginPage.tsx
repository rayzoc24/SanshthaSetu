/**
 * LoginPage
 *
 * - Accepts email + password
 * - Calls POST /auth/login via apiClient
 * - On success: stores credentials in Zustand, navigates to role portal
 * - On failure: displays the API error message in a destructive Alert
 * - Loading state: button disabled + "Signing in…" label while request is in flight
 */

import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AxiosError } from 'axios'

import apiClient from '@/api/client'
import { useAuthStore, ROLE_PORTAL } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LoginResponse {
  access_token: string
  token_type: string
  role: string
}

interface ApiErrorBody {
  detail: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Decode a JWT payload without verifying the signature.
 * Used client-side only to extract sub (userId) and email after login.
 */
function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split('.')[1]
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return {}
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const { data } = await apiClient.post<LoginResponse>('/auth/login', {
        email,
        password,
      })

      // Decode userId and email from the JWT payload (no server round-trip needed).
      const payload = decodeJwtPayload(data.access_token)
      const userId = (payload.sub as string | undefined) ?? ''
      const userEmail = (payload.email as string | undefined) ?? email

      setAuth(data.access_token, data.role, userId, userEmail)

      // Redirect to the role-appropriate portal.
      const destination = ROLE_PORTAL[data.role] ?? '/login'
      navigate(destination, { replace: true })
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorBody>
      const message =
        axiosErr.response?.data?.detail ??
        'An unexpected error occurred. Please try again.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">

        {/* Heading */}
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            SanshthaSetu
          </h1>
          <p className="text-sm text-muted-foreground">
            AICTE Approval Workflow Platform
          </p>
        </div>

        {/* Error alert */}
        {error && (
          <Alert variant="destructive" role="alert">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-1">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              aria-required="true"
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              aria-required="true"
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={loading || !email || !password}
            aria-busy={loading}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

      </div>
    </div>
  )
}
