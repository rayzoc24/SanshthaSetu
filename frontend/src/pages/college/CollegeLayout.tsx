import AppShell from '@/components/AppShell'

export default function CollegeLayout() {
  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Institution Portal</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Enter campus infrastructure details, evaluate readiness against published handbook norms, and submit applications.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Infrastructure Assessment</span>
            <p className="text-xl font-bold text-foreground">Module 2</p>
            <p className="text-xs text-muted-foreground">Automatic gap analysis (Met / Partial / Missing)</p>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Compliance & Undertakings</span>
            <p className="text-xl font-bold text-foreground">Module 5</p>
            <p className="text-xs text-muted-foreground">Post-approval lease and document monitoring</p>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
