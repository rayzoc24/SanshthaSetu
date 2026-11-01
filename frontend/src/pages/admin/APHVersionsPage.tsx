/**
 * APH Versions Management Page (/admin/aph)
 * Lists uploaded handbook versions, extraction status, and navigation to rule review.
 */

import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/api/client'
import { Button } from '@/components/ui/button'

interface AphVersion {
  id: string
  version_label: string
  file_name: string | null
  status: 'draft' | 'published'
  extraction_status: 'none' | 'running' | 'done' | 'failed'
  effective_date: string | null
  created_at: string
}

export default function APHVersionsPage() {
  const { data: versions, isLoading, error } = useQuery<AphVersion[]>({
    queryKey: ['aph_versions'],
    queryFn: async () => {
      const res = await apiClient.get<AphVersion[]>('/aph/versions')
      return res.data
    },
    refetchInterval: 4000, // Poll for background extraction status
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gov-green/10 text-gov-green border border-gov-green/20">Published</span>
      case 'draft':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground border border-border">Draft</span>
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">{status}</span>
    }
  }

  const getExtractionBadge = (status: string) => {
    switch (status) {
      case 'done':
        return <span className="text-xs font-medium text-gov-green">✓ Extracted</span>
      case 'running':
        return <span className="text-xs font-medium text-gov-saffron animate-pulse">⏳ Extracting Rules…</span>
      case 'failed':
        return <span className="text-xs font-medium text-destructive">⚠ Extraction Failed</span>
      default:
        return <span className="text-xs text-muted-foreground">Not Started</span>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">APH Handbook Versions</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Upload new handbook PDFs, trigger AI norm extraction, review draft rules, and publish authoritative versions.
          </p>
        </div>
        <Link to="/admin/aph/upload">
          <Button className="font-semibold cursor-pointer">
            + Upload New Handbook
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-muted-foreground">Loading handbook versions…</div>
      ) : error ? (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md border border-destructive/20 text-sm">
          Failed to load handbook versions.
        </div>
      ) : versions && versions.length === 0 ? (
        <div className="text-center p-12 bg-card border border-border rounded-lg space-y-3">
          <p className="text-muted-foreground font-medium">No handbook versions uploaded yet.</p>
          <Link to="/admin/aph/upload">
            <Button variant="outline">Upload your first APH PDF</Button>
          </Link>
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden bg-card shadow-xs">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 border-b border-border text-xs uppercase font-semibold text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Version Title</th>
                <th className="px-4 py-3">File Name</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">AI Extraction</th>
                <th className="px-4 py-3">Effective Date</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {versions?.map((v) => (
                <tr key={v.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-semibold text-foreground">{v.version_label}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{v.file_name || '—'}</td>
                  <td className="px-4 py-3">{getStatusBadge(v.status)}</td>
                  <td className="px-4 py-3">{getExtractionBadge(v.extraction_status)}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{v.effective_date || 'Not set'}</td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Link to={`/admin/aph/${v.id}/rules`}>
                      <Button variant="outline" size="sm" className="text-xs">
                        Review Rules →
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
