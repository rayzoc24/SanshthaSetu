/**
 * App.tsx — complete route configuration including Module 1 APH pages.
 */

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ErrorBoundary } from '@/components/ErrorBoundary'
import ProtectedRoute from '@/components/ProtectedRoute'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import CollegeLayout from '@/pages/college/CollegeLayout'
import AdminLayout from '@/pages/admin/AdminLayout'
import EVCLayout from '@/pages/evc/EVCLayout'
import APHVersionsPage from '@/pages/admin/APHVersionsPage'
import APHUploadPage from '@/pages/admin/APHUploadPage'
import APHRulesPage from '@/pages/admin/APHRulesPage'
import NotFoundPage from '@/pages/NotFoundPage'

/** Roles that may access the admin portal. */
const ADMIN_ROLES = [
  'main_admin',
  'regional_officer',
  'bureau_officer',
  'competent_authority',
]

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          {/* Root → login */}
          <Route path="/" element={<Navigate to="/login" replace />} />

          {/* Public */}
          <Route path="/login" element={<LoginPage />} />

          {/* Generic dashboard (accessible by all authenticated roles) */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute roles={['college_admin', ...ADMIN_ROLES, 'evc_member']}>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

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
            path="/admin"
            element={
              <ProtectedRoute roles={ADMIN_ROLES}>
                <AdminLayout />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/aph"
            element={
              <ProtectedRoute roles={['main_admin']}>
                <AdminLayout>
                  <APHVersionsPage />
                </AdminLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/aph/upload"
            element={
              <ProtectedRoute roles={['main_admin']}>
                <AdminLayout>
                  <APHUploadPage />
                </AdminLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/aph/:id/rules"
            element={
              <ProtectedRoute roles={['main_admin']}>
                <AdminLayout>
                  <APHRulesPage />
                </AdminLayout>
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

          {/* 404 Catch-all */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
