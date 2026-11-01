/**
 * AppShell — Clean, modern portal layout for SanshthaSetu.
 *
 * Includes:
 * - Professional header with portal branding
 * - User badge & Sign out button
 * - Role-aware sidebar navigation
 * - Main content container
 * - Prototype disclaimer footer
 */

import { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/button'

interface NavItem {
  label: string
  to: string
  end?: boolean
}

interface AppShellProps {
  children?: ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const navigate = useNavigate()
  const { role, email, clearAuth } = useAuthStore()

  function handleLogout() {
    clearAuth()
    navigate('/login', { replace: true })
  }

  const formatRole = (r: string | null) => {
    if (!r) return 'GUEST'
    return r.replace(/_/g, ' ').toUpperCase()
  }

  // Derive role-specific navigation items
  const getNavItems = (): NavItem[] => {
    switch (role) {
      case 'college_admin':
        return [
          { label: 'Dashboard', to: '/college', end: true },
          { label: 'Infrastructure Data', to: '/college/readiness/enter' },
          { label: 'Readiness Gap Report', to: '/college/readiness/report' },
          { label: 'Applications', to: '/college/applications' },
        ]
      case 'main_admin':
        return [
          { label: 'Dashboard', to: '/admin', end: true },
          { label: 'APH Handbooks & Rules', to: '/admin/aph' },
          { label: 'All Applications', to: '/admin/applications' },
          { label: 'Institutions', to: '/admin/institutions' },
        ]
      case 'regional_officer':
        return [
          { label: 'Regional Dashboard', to: '/admin', end: true },
          { label: 'Application Scrutiny', to: '/admin/applications' },
          { label: 'EVC Assignments', to: '/admin/evc-assignments' },
        ]
      case 'bureau_officer':
      case 'competent_authority':
        return [
          { label: 'Review Dashboard', to: '/admin', end: true },
          { label: 'Applications', to: '/admin/applications' },
        ]
      case 'evc_member':
        return [
          { label: 'Inspection Queue', to: '/evc', end: true },
          { label: 'Digital Checklists', to: '/evc/checklists' },
          { label: 'Submitted Reports', to: '/evc/reports' },
        ]
      default:
        return [{ label: 'Overview', to: '/dashboard', end: true }]
    }
  }

  const navItems = getNavItems()

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground antialiased selection:bg-accent selection:text-accent-foreground">
      {/* Top Accent Stripe */}
      <div className="h-1 w-full bg-primary" />

      {/* Main Header */}
      <header className="border-b border-border bg-card px-4 lg:px-8 py-3.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-md bg-primary text-primary-foreground flex items-center justify-center font-bold text-base shadow-xs">
            SS
          </div>

          <div>
            <span className="font-bold text-lg text-foreground tracking-tight">SanshthaSetu</span>
            <p className="text-xs text-muted-foreground font-normal">
              Integrated Approval Workflow Automation & Compliance Monitoring
            </p>
          </div>
        </div>

        {/* User profile & actions */}
        <div className="flex items-center space-x-4">
          <div className="hidden sm:block text-right">
            <p className="text-sm font-medium text-foreground leading-tight">{email}</p>
            <div className="flex items-center justify-end space-x-1.5 mt-0.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-gov-green" />
              <span className="text-xs font-semibold text-primary">{formatRole(role)}</span>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="text-xs font-medium cursor-pointer"
          >
            Sign Out
          </Button>
        </div>
      </header>

      {/* Body: Sidebar + Main Content */}
      <div className="flex flex-1">
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-border bg-card/60 p-4 hidden md:flex flex-col justify-between">
          <nav className="space-y-1.5" aria-label="Portal Navigation">
            <div className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground/80">
              Navigation Menu
            </div>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                      : 'text-foreground/80 hover:bg-muted hover:text-foreground'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="p-3 bg-muted/40 rounded-md border border-border text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-foreground">SanshthaSetu Platform</p>
            <p>Integrated Compliance System</p>
            <p className="text-gov-green font-medium pt-1">● Session Active</p>
          </div>
        </aside>

        {/* Content Slot */}
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Sticky Prototype Footer */}
      <footer className="border-t border-border bg-card/80 px-6 py-3 text-center text-xs text-muted-foreground">
        <p>
          SanshthaSetu — Prototype for Smart India Hackathon (SIH 2026) | Problem Statement: SIH26262 | Team Port2Code
        </p>
      </footer>
    </div>
  )
}
