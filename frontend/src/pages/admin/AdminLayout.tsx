import { ReactNode } from 'react'
import AppShell from '@/components/AppShell'

interface AdminLayoutProps {
  children?: ReactNode
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  if (children) {
    return <AppShell>{children}</AppShell>
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Admin Workspace</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage APH versions, scrutinize institution applications, and track statutory decisions.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">APH Extraction</span>
            <p className="text-2xl font-bold text-foreground">Operational</p>
            <p className="text-xs text-muted-foreground">PDF handbook rules pipeline</p>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Applications</span>
            <p className="text-2xl font-bold text-foreground">Module 3</p>
            <p className="text-xs text-muted-foreground">Stage-wise scrutiny & approval</p>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Database Sync</span>
            <p className="text-2xl font-bold text-gov-green">Live</p>
            <p className="text-xs text-muted-foreground">Neon Postgres & Object Storage</p>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
