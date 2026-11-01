/**
 * APH Upload & Extraction Trigger Page (/admin/aph/upload)
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function APHUploadPage() {
  const navigate = useNavigate()
  const [versionLabel, setVersionLabel] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !versionLabel) return

    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append('version_label', versionLabel)
    formData.append('file', file)

    try {
      const res = await apiClient.post<{ id: string }>('/aph/versions', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      navigate(`/admin/aph/${res.data.id}/rules`)
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to upload APH PDF handbook.'
      setError(message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="border-b border-border pb-3">
        <h2 className="text-2xl font-bold tracking-tight text-foreground">Upload Approval Process Handbook</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Upload official AICTE APH PDF document to store pages and initiate normative rule extraction.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleUpload} className="bg-card border border-border p-6 rounded-lg shadow-xs space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="versionLabel" className="text-xs font-semibold">
            Handbook Version Label / Academic Year
          </Label>
          <Input
            id="versionLabel"
            placeholder="e.g. APH 2026-27 (Revised Norms)"
            value={versionLabel}
            onChange={(e) => setVersionLabel(e.target.value)}
            required
            disabled={uploading}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pdfFile" className="text-xs font-semibold">
            Handbook Document (PDF Format, max 25 MB)
          </Label>
          <Input
            id="pdfFile"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
            disabled={uploading}
          />
          <p className="text-xs text-muted-foreground">
            Pages will be parsed with PyMuPDF and stored for AI review.
          </p>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/admin/aph')}
            disabled={uploading}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={uploading || !file || !versionLabel}>
            {uploading ? 'Uploading & Parsing Pages…' : 'Upload Handbook'}
          </Button>
        </div>
      </form>
    </div>
  )
}

