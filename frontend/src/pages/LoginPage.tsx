/**
 * LoginPage — Clean, modern authentication screen for SanshthaSetu.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AxiosError } from 'axios'

import apiClient from '@/api/client'
import { useAuthStore, ROLE_PORTAL } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface LoginResponse {
  access_token: string
  token_type: string
  role: string
}

interface ApiErrorBody {
  detail: string
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split('.')[1]
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return {}
  }
}

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

      const payload = decodeJwtPayload(data.access_token)
      const userId = (payload.sub as string | undefined) ?? ''
      const userEmail = (payload.email as string | undefined) ?? email

      setAuth(data.access_token, data.role, userId, userEmail)

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
    <div className="min-h-screen flex flex-col bg-background selection:bg-accent selection:text-accent-foreground">
      {/* Top Accent Stripe */}
      <div className="h-1 w-full bg-primary" />

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Platform Branding Header */}
          <div className="space-y-3 text-center">
            <div className="inline-flex h-12 w-12 rounded-lg bg-primary text-primary-foreground items-center justify-center font-bold text-xl shadow-sm">
              SS
            </div>

            <div>
              <h1 className="font-extrabold text-2xl text-foreground tracking-tight">
                SanshthaSetu
              </h1>
              <p className="text-xs text-muted-foreground font-medium mt-1">
                Approval Workflow Automation & Compliance Monitoring Platform
              </p>
            </div>
          </div>

          {/* Form Card */}
          <div className="bg-card border border-border rounded-lg shadow-sm p-6 sm:p-8 space-y-5">
            <div className="border-b border-border pb-3">
              <h2 className="text-lg font-bold text-foreground">Sign In to Your Account</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Institution Representatives & Administrative Users
              </p>
            </div>

            {error && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-xs font-semibold text-foreground">
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  aria-required="true"
                  className="bg-background"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-xs font-semibold text-foreground">
                    Password
                  </Label>
                </div>
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
                  className="bg-background"
                />
              </div>

              <Button
                type="submit"
                className="w-full font-semibold cursor-pointer"
                disabled={loading || !email || !password}
                aria-busy={loading}
              >
                {loading ? 'Authenticating…' : 'Sign In'}
              </Button>
            </form>
          </div>

          {/* Demonstration Notice */}
          <div className="text-center text-xs text-muted-foreground space-y-1">
            <p>Smart India Hackathon 2026 Prototype (Team Port2Code)</p>
            <p className="text-muted-foreground/80">Role-Based Access Control</p>
          </div>
        </div>
      </div>

      <footer className="border-t border-border py-3 text-center text-xs text-muted-foreground">
        SanshthaSetu Platform — Prototype
      </footer>
    </div>
  )
}
