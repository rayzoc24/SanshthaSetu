import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="max-w-md w-full bg-card p-8 rounded-lg border border-border shadow-sm text-center space-y-4">
        <div className="inline-block px-3 py-1 bg-muted rounded-full text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          404 Not Found
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Page Not Found</h1>
        <p className="text-sm text-muted-foreground">
          The requested URL does not exist or has been relocated within SanshthaSetu.
        </p>
        <div className="pt-2">
          <Link to="/">
            <Button className="w-full">Return to Dashboard</Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
