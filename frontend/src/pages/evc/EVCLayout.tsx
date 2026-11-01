import AppShell from '@/components/AppShell'

export default function EVCLayout() {
  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="border-b border-border pb-4">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Expert Visiting Committee (EVC) Desk</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Conduct on-site inspections using digital checklists and submit verified evaluation reports.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-5 space-y-2 shadow-xs">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Digital Inspection</span>
          <p className="text-xl font-bold text-foreground">Module 4</p>
          <p className="text-xs text-muted-foreground">Paperless checklists with geotagged document verification</p>
        </div>
      </div>
    </AppShell>
  )
}
