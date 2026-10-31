/**
 * App.tsx — root router configuration.
 *
 * Route map:
 *   /              → redirect to /login
 *   /login         → LoginPage          (public)
 *   /college/*     → CollegeLayout      (requires college_admin)
 *   /admin/*       → AdminLayout        (requires any admin-side role)
 *   /evc/*         → EVCLayout          (requires evc_member)
 *   *              → redirect to /login (catch-all)
 */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from '@/components/ProtectedRoute'
import LoginPage from '@/pages/LoginPage'
import CollegeLayout from '@/pages/college/CollegeLayout'
import AdminLayout from '@/pages/admin/AdminLayout'
import EVCLayout from '@/pages/evc/EVCLayout'

/** Roles that may access the admin portal. */
const ADMIN_ROLES = [
  'main_admin',
  'regional_officer',
  'bureau_officer',
  'competent_authority',
]

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Root → login */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* College portal */}
        <Route
          path="/college/*"
          element={
            <ProtectedRoute roles={['college_admin']}>
              <CollegeLayout />
            </ProtectedRoute>
          }
        />

        {/* Admin portal */}
        <Route
          path="/admin/*"
          element={
            <ProtectedRoute roles={ADMIN_ROLES}>
              <AdminLayout />
            </ProtectedRoute>
          }
        />

        {/* EVC portal */}
        <Route
          path="/evc/*"
          element={
            <ProtectedRoute roles={['evc_member']}>
              <EVCLayout />
            </ProtectedRoute>
          }
        />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
