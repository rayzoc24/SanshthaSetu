import AppShell from '@/components/AppShell'
import { useAuthStore } from '@/store/authStore'

export default function DashboardPage() {
  const { role, email } = useAuthStore()

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            {role === 'main_admin'
              ? 'Apex Administration Console'
              : role === 'college_admin'
              ? 'Institution Portal'
              : role === 'evc_member'
              ? 'Inspection Committee Workspace'
              : 'Officer Scrutiny Desk'}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Logged in as <span className="font-medium text-foreground">{email}</span>. Select a module from the sidebar to proceed.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Portal Status</span>
            <p className="text-2xl font-bold text-foreground">Operational</p>
            <p className="text-xs text-muted-foreground">Theme: UX4G Government Spec</p>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Database</span>
            <p className="text-2xl font-bold text-gov-green">Connected</p>
            <p className="text-xs text-muted-foreground">Neon Lakebase Postgres (Live)</p>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Object Storage</span>
            <p className="text-2xl font-bold text-primary">Provisioned</p>
            <p className="text-xs text-muted-foreground">Neon S3-Compatible Bucket</p>
          </div>
        </div>
      </div>
    </AppShell>
  )
}

