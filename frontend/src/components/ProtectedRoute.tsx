/**
 * ProtectedRoute
 *
 * Wraps a route that requires authentication and a specific set of roles.
 *
 * Behaviour:
 *  - No token          → redirect to /login
 *  - Token present, role allowed  → render children
 *  - Token present, role NOT allowed → redirect to the user's correct portal
 *    (never to /login, because they ARE authenticated — just in the wrong place)
 */

import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore, ROLE_PORTAL } from '@/store/authStore'

interface ProtectedRouteProps {
  /** Roles that are permitted to access this route. */
  roles: string[]
  children: ReactNode
}

export default function ProtectedRoute({ roles, children }: ProtectedRouteProps) {
  const { token, role } = useAuthStore()

  // 1. Not authenticated → send to login.
  if (!token || !role) {
    return <Navigate to="/login" replace />
  }

  // 2. Authenticated but wrong portal → redirect to the correct one.
  if (!roles.includes(role)) {
    const correctPath = ROLE_PORTAL[role] ?? '/login'
    return <Navigate to={correctPath} replace />
  }

  // 3. Authorised → render the protected content.
  return <>{children}</>
}
