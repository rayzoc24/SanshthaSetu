/**
 * APH Rules Review & Publish Page (/admin/aph/:id/rules)
 */

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface AphRule {
  id: string
  programme: string
  programme_key: string
  category: string
  parameter: string
  parameter_key: string
  operator: string
  numeric_value: number | null
  string_value: string | null
  unit: string | null
  source_page: number | null
  source_quote: string | null
  needs_review: boolean
  is_ai_suggested: boolean
}

interface AphVersionDetail {
  id: string
  version_label: string
  file_name: string | null
  status: 'draft' | 'published'
  extraction_status: 'none' | 'running' | 'done' | 'failed'
  effective_date: string | null
  notes: string | null
}

export default function APHRulesPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split('T')[0])
  const [publishError, setPublishError] = useState<string | null>(null)
  
  // Fetch Version Detail
  const { data: version } = useQuery<AphVersionDetail>({
    queryKey: ['aph_version', id],
    queryFn: async () => {
      const res = await apiClient.get<AphVersionDetail>(`/aph/versions/${id}`)
      return res.data
    },
    refetchInterval: (query) => (query.state.data?.extraction_status === 'running' ? 3000 : false),
  })

  // Fetch Rules
  const { data: rules, isLoading: rulesLoading } = useQuery<AphRule[]>({
    queryKey: ['aph_rules', id],
    queryFn: async () => {
      const res = await apiClient.get<AphRule[]>(`/aph/versions/${id}/rules`)
      return res.data
    },
    refetchInterval: () => (version?.extraction_status === 'running' ? 3000 : false),
  })

  // Trigger Extraction Mutation
  const extractMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.post(`/aph/versions/${id}/extract?page_start=1&page_end=15&force=true`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['aph_version', id] })
      queryClient.invalidateQueries({ queryKey: ['aph_rules', id] })
    },
  })

  // Publish Mutation
  const publishMutation = useMutation({
    mutationFn: async () => {
      return await apiClient.post(`/aph/versions/${id}/publish`, {
        effective_date: effectiveDate,
      })
    },
    onSuccess: () => {
      setPublishError(null)
      queryClient.invalidateQueries({ queryKey: ['aph_version', id] })
      queryClient.invalidateQueries({ queryKey: ['aph_versions'] })
    },
    onError: (err: any) => {
      setPublishError(err.response?.data?.detail || 'Failed to publish handbook version.')
    },
  })

  // Fetch PDF signed URL
  async function openPdfUrl() {
    try {
      const res = await apiClient.get<{ signed_url: string }>(`/aph/versions/${id}/pdf-url`)
      window.open(res.data.signed_url, '_blank')
    } catch {
      alert('Could not fetch signed PDF URL.')
    }
  }

  const unreviewedCount = rules?.filter((r) => r.needs_review).length || 0
  const isDraft = version?.status === 'draft'

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border pb-4 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link to="/admin/aph" className="text-xs text-muted-foreground hover:underline">
              ← Back to Versions
            </Link>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground mt-1">
            {version?.version_label || 'Handbook Rules'}
          </h2>
          <p className="text-xs text-muted-foreground">
            Status: <span className="font-semibold uppercase">{version?.status}</span> | AI Extraction:{' '}
            <span className="font-semibold">{version?.extraction_status}</span>
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {version?.file_name && (
            <Button variant="outline" size="sm" onClick={openPdfUrl}>
              📄 View Source PDF
            </Button>
          )}

          {isDraft && (
            <Button
              variant="secondary"
              size="sm"
              disabled={version?.extraction_status === 'running' || extractMutation.isPending}
              onClick={() => extractMutation.mutate()}
            >
              {version?.extraction_status === 'running' ? '⏳ AI Extracting…' : '⚡ Run AI Extraction'}
            </Button>
          )}
        </div>
      </div>

      {version?.extraction_status === 'failed' && (
        <Alert variant="destructive">
          <AlertTitle className="font-semibold text-sm">Rule Extraction Failed</AlertTitle>
          <AlertDescription className="text-xs mt-1">
            <p>{version?.notes || 'An unexpected error occurred during extraction. Check GEMINI_API_KEY or use fallback parser.'}</p>
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => extractMutation.mutate()}
                disabled={extractMutation.isPending}
                className="text-xs bg-background"
              >
                🔄 Retry Extraction
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {version?.notes && version?.extraction_status === 'done' && (
        <Alert className="bg-primary/5 border-primary/20 text-xs">
          <AlertDescription className="text-muted-foreground flex items-center justify-between">
            <span>💡 <strong>Extraction Note:</strong> {version.notes}</span>
          </AlertDescription>
        </Alert>
      )}

      {publishError && (
        <Alert variant="destructive">
          <AlertDescription>{publishError}</AlertDescription>
        </Alert>
      )}

      {/* Publish Bar for Draft versions */}
      {isDraft && (
        <div className="bg-card border border-border p-4 rounded-lg flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xs">
          <div>
            <p className="font-semibold text-sm">Publish Handbook Version</p>
            <p className="text-xs text-muted-foreground">
              Once published, this ruleset becomes immutable and active for college infrastructure readiness assessments.
            </p>
            {unreviewedCount > 0 && (
              <p className="text-xs text-destructive font-medium mt-1">
                ⚠ {unreviewedCount} rule(s) require review before publishing can be completed.
              </p>
            )}
          </div>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <Input
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              className="text-xs max-w-[160px]"
            />
            <Button
              size="sm"
              disabled={unreviewedCount > 0 || (rules?.length || 0) === 0 || publishMutation.isPending}
              onClick={() => publishMutation.mutate()}
            >
              {publishMutation.isPending ? 'Publishing…' : 'Publish Version'}
            </Button>
          </div>
        </div>
      )}

      {/* Rules Table */}
      <div className="border border-border rounded-lg overflow-hidden bg-card shadow-xs">
        <div className="p-4 bg-muted/30 border-b border-border flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Extracted Rules ({rules?.length || 0})
          </p>
        </div>

        {rulesLoading ? (
          <div className="p-8 text-center text-muted-foreground text-sm">Loading rules…</div>
        ) : !rules || rules.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            No rules recorded for this handbook yet. Click "Run AI Extraction" to parse the document.
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 border-b border-border text-xs uppercase font-semibold text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Parameter</th>
                <th className="px-4 py-3">Condition</th>
                <th className="px-4 py-3">Source Quote</th>
                <th className="px-4 py-3">Tag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rules.map((r) => (
                <tr key={r.id} className="hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-3 text-xs font-medium text-muted-foreground">{r.category}</td>
                  <td className="px-4 py-3">
                    <p className="font-semibold text-foreground text-sm leading-tight">{r.parameter}</p>
                    <p className="text-xs text-muted-foreground font-mono">{r.parameter_key}</p>
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-foreground">
                    {r.operator} {r.numeric_value !== null ? `${r.numeric_value} ${r.unit || ''}` : r.string_value}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground max-w-sm italic">
                    "{r.source_quote || 'No quote recorded'}" (p. {r.source_page || '—'})
                  </td>
                  <td className="px-4 py-3 space-x-1">
                    {r.is_ai_suggested && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
                        AI-suggested
                      </span>
                    )}
                    {r.needs_review && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-destructive/10 text-destructive border border-destructive/20">
                        Needs Review
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
