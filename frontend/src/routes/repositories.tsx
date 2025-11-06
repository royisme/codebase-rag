import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ingestApi, IngestRepoResponse } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { GitBranch, FolderGit2, Upload, CheckCircle2 } from 'lucide-react'

export const Route = createFileRoute('/repositories')({
  component: RepositoriesPage,
})

function RepositoriesPage() {
  const [formData, setFormData] = useState({
    repoUrl: '',
    localPath: '',
    branch: 'main',
    mode: 'full' as 'full' | 'incremental',
  })
  const [lastResult, setLastResult] = useState<IngestRepoResponse | null>(null)

  const ingestMutation = useMutation({
    mutationFn: ingestApi.ingestRepo,
    onSuccess: (response) => {
      setLastResult(response.data)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    ingestMutation.mutate({
      repo_url: formData.repoUrl || undefined,
      local_path: formData.localPath || undefined,
      branch: formData.branch,
      mode: formData.mode,
      include_globs: ['**/*.py', '**/*.ts', '**/*.tsx', '**/*.java', '**/*.php', '**/*.go'],
      exclude_globs: ['**/node_modules/**', '**/.git/**', '**/__pycache__/**', '**/.venv/**', '**/vendor/**', '**/target/**'],
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Repositories</h1>
        <p className="text-muted-foreground">
          Ingest and manage code repositories
        </p>
      </div>

      {/* Ingest Form */}
      <Card>
        <CardHeader>
          <CardTitle>Ingest Repository</CardTitle>
          <CardDescription>
            Add a new repository to the knowledge graph
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Repository URL */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Repository URL (Git)
              </label>
              <div className="flex items-center space-x-2">
                <GitBranch className="w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  className="flex-1 px-3 py-2 border rounded-md"
                  placeholder="https://github.com/owner/repo.git"
                  value={formData.repoUrl}
                  onChange={(e) => setFormData({ ...formData, repoUrl: e.target.value })}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Or use local path below
              </p>
            </div>

            {/* Local Path */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Local Path
              </label>
              <div className="flex items-center space-x-2">
                <FolderGit2 className="w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  className="flex-1 px-3 py-2 border rounded-md"
                  placeholder="/path/to/local/repo"
                  value={formData.localPath}
                  onChange={(e) => setFormData({ ...formData, localPath: e.target.value })}
                />
              </div>
            </div>

            {/* Branch */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Branch</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="main"
                  value={formData.branch}
                  onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Mode</label>
                <select
                  className="w-full px-3 py-2 border rounded-md"
                  value={formData.mode}
                  onChange={(e) => setFormData({ ...formData, mode: e.target.value as 'full' | 'incremental' })}
                >
                  <option value="full">Full</option>
                  <option value="incremental">Incremental</option>
                </select>
              </div>
            </div>

            {/* Supported Languages */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Supported Languages</label>
              <div className="flex flex-wrap gap-2">
                {['Python', 'TypeScript', 'JavaScript', 'Java', 'PHP', 'Go'].map((lang) => (
                  <Badge key={lang} variant="secondary">{lang}</Badge>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full"
              disabled={ingestMutation.isPending || (!formData.repoUrl && !formData.localPath)}
            >
              {ingestMutation.isPending ? (
                <>Processing...</>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Ingest Repository
                </>
              )}
            </Button>
          </form>

          {/* Result */}
          {ingestMutation.isSuccess && lastResult && (
            <div className="mt-4 p-4 border rounded-lg bg-green-50 dark:bg-green-950">
              <div className="flex items-center space-x-2 text-green-800 dark:text-green-200">
                <CheckCircle2 className="w-5 h-5" />
                <div>
                  <p className="font-medium">Ingestion started successfully!</p>
                  <p className="text-sm">Task ID: {lastResult.task_id}</p>
                  {lastResult.files_processed && (
                    <p className="text-sm">Files processed: {lastResult.files_processed}</p>
                  )}
                  {lastResult.mode && (
                    <p className="text-sm">Mode: {lastResult.mode}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {ingestMutation.isError && (
            <div className="mt-4 p-4 border rounded-lg bg-red-50 dark:bg-red-950">
              <p className="text-red-800 dark:text-red-200 text-sm">
                Error: {(ingestMutation.error as Error & { response?: { data?: { detail?: string } } })?.response?.data?.detail || (ingestMutation.error as Error).message}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Full Ingestion</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Processes all files in the repository. Use this for the first ingestion or when you want to rebuild the entire graph.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Incremental Ingestion</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Only processes changed files since the last ingestion. Much faster for large repositories with few changes.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
