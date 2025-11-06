import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { taskApi, TaskStatus } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { Clock, CheckCircle2, XCircle, AlertCircle, Loader2, PlayCircle, Upload, FolderOpen, XIcon, Info } from 'lucide-react'
import { formatDistance } from 'date-fns'
import { useState } from 'react'

export const Route = createFileRoute('/tasks')({
  component: TasksPage,
})

function TasksPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [selectedTask, setSelectedTask] = useState<TaskStatus | null>(null)
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)

  // File upload state
  const [uploadMessage, setUploadMessage] = useState<string>('')

  // Directory processing state
  const [directoryPath, setDirectoryPath] = useState('')
  const [filePatterns, setFilePatterns] = useState('*.txt, *.md, *.py')

  const { data: tasksData, isLoading, refetch } = useQuery({
    queryKey: ['tasks', statusFilter],
    queryFn: () => taskApi.listTasks({
      limit: 50,
      ...(statusFilter && { status: statusFilter })
    }).then(res => res.data),
    refetchInterval: 3000,
  })

  const cancelMutation = useMutation({
    mutationFn: (taskId: string) => taskApi.cancelTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const content = await file.text()
      const filename = file.name
      const extension = filename.split('.').pop()?.toLowerCase() || 'txt'

      const typeMapping: Record<string, string> = {
        'txt': 'text',
        'md': 'markdown',
        'py': 'python',
        'js': 'javascript',
        'java': 'java',
        'sql': 'sql',
        'json': 'json',
        'xml': 'xml',
        'html': 'html',
      }

      const document_type = typeMapping[extension] || 'text'

      return taskApi.processDocument({ content, filename, document_type })
    },
    onSuccess: (data) => {
      setUploadMessage(`File uploaded successfully! Task ID: ${data.data.task_id}`)
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
    onError: (error: Error) => {
      setUploadMessage(`Upload failed: ${error.message}`)
    },
  })

  const directoryMutation = useMutation({
    mutationFn: (params: { directory_path: string; file_patterns: string[] }) =>
      taskApi.processDirectory(params),
    onSuccess: (data) => {
      alert(`Directory processing started! Task ID: ${data.data.task_id}`)
      setDirectoryPath('')
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
    onError: (error: Error) => {
      alert(`Failed to process directory: ${error.message}`)
    },
  })

  const tasks = tasksData?.tasks || []

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-600" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-600" />
      default:
        return <AlertCircle className="w-4 h-4 text-gray-600" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'destructive' | 'default' | 'warning' | 'secondary' | 'outline'> = {
      success: 'success',
      failed: 'destructive',
      running: 'default',
      pending: 'warning',
      cancelled: 'secondary',
    }
    return <Badge variant={variants[status] || 'outline'}>{status}</Badge>
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const fileSize = file.size
    const maxSize = 50 * 1024 // 50KB

    if (fileSize > maxSize) {
      setUploadMessage(`File too large (${(fileSize / 1024).toFixed(1)}KB)! Maximum size: 50KB. Please use directory processing for larger files.`)
      return
    }

    uploadMutation.mutate(file)
  }

  const handleDirectoryProcessing = () => {
    if (!directoryPath.trim()) {
      alert('Please enter a directory path')
      return
    }

    const patterns = filePatterns.split(',').map(p => p.trim()).filter(p => p)
    if (patterns.length === 0) {
      alert('Please enter at least one file pattern')
      return
    }

    directoryMutation.mutate({
      directory_path: directoryPath,
      file_patterns: patterns,
    })
  }

  const handleViewDetails = (task: TaskStatus) => {
    setSelectedTask(task)
    setIsDetailsOpen(true)
  }

  const handleCancelTask = (taskId: string) => {
    if (confirm('Are you sure you want to cancel this task?')) {
      cancelMutation.mutate(taskId)
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  const statusCounts = tasks.reduce((acc, task) => {
    acc[task.status] = (acc[task.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tasks Monitor</h1>
          <p className="text-muted-foreground">
            Monitor and manage document processing tasks
          </p>
        </div>
        <Button onClick={() => refetch()}>
          <PlayCircle className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total</CardDescription>
            <CardTitle className="text-2xl">{tasks.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Running</CardDescription>
            <CardTitle className="text-2xl text-blue-600">
              {statusCounts.running || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pending</CardDescription>
            <CardTitle className="text-2xl text-yellow-600">
              {statusCounts.pending || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Success</CardDescription>
            <CardTitle className="text-2xl text-green-600">
              {statusCounts.success || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Failed</CardDescription>
            <CardTitle className="text-2xl text-red-600">
              {statusCounts.failed || 0}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* File Upload & Directory Processing */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* File Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Upload className="w-5 h-5 mr-2" />
              File Upload
            </CardTitle>
            <CardDescription>Upload a single file for processing (max 50KB)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="file-upload">Select File</Label>
              <Input
                id="file-upload"
                type="file"
                onChange={handleFileUpload}
                accept=".txt,.md,.py,.js,.java,.sql,.json,.xml,.html"
                className="mt-2"
                disabled={uploadMutation.isPending}
              />
            </div>
            {uploadMessage && (
              <p className={`text-sm ${uploadMessage.includes('success') ? 'text-green-600' : 'text-red-600'}`}>
                {uploadMessage}
              </p>
            )}
            {uploadMutation.isPending && (
              <div className="flex items-center text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading and processing...
              </div>
            )}
          </CardContent>
        </Card>

        {/* Directory Processing Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <FolderOpen className="w-5 h-5 mr-2" />
              Directory Processing
            </CardTitle>
            <CardDescription>Process multiple files from a directory</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="directory-path">Directory Path</Label>
              <Input
                id="directory-path"
                value={directoryPath}
                onChange={(e) => setDirectoryPath(e.target.value)}
                placeholder="/path/to/documents"
                className="mt-2"
              />
            </div>
            <div>
              <Label htmlFor="file-patterns">File Patterns (comma-separated)</Label>
              <Input
                id="file-patterns"
                value={filePatterns}
                onChange={(e) => setFilePatterns(e.target.value)}
                placeholder="*.txt, *.md, *.py"
                className="mt-2"
              />
            </div>
            <Button
              onClick={handleDirectoryProcessing}
              disabled={directoryMutation.isPending}
              className="w-full"
            >
              {directoryMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Process Directory
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Tasks List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Tasks</CardTitle>
              <CardDescription>All processing tasks</CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Label htmlFor="status-filter">Filter:</Label>
              <Select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-32"
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="running">Running</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {tasks.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No tasks found
              </div>
            ) : (
              tasks.map((task) => (
                <div
                  key={task.task_id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
                >
                  <div className="flex items-center space-x-4 flex-1 min-w-0">
                    {getStatusIcon(task.status)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{task.task_id}</p>
                      <p className="text-sm text-muted-foreground truncate">
                        {task.message || 'Processing...'}
                      </p>
                      {task.error && (
                        <p className="text-sm text-red-600 truncate mt-1">
                          Error: {task.error}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-4">
                    {task.status === 'running' && (
                      <div className="w-32">
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-600 transition-all"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {task.progress.toFixed(0)}%
                        </p>
                      </div>
                    )}

                    {getStatusBadge(task.status)}

                    <p className="text-xs text-muted-foreground w-24 text-right">
                      {formatDistance(new Date(task.created_at), new Date(), {
                        addSuffix: true,
                      })}
                    </p>

                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleViewDetails(task)}
                      >
                        <Info className="w-4 h-4" />
                      </Button>
                      {(task.status === 'pending' || task.status === 'running') && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleCancelTask(task.task_id)}
                          disabled={cancelMutation.isPending}
                        >
                          <XIcon className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Task Details Dialog */}
      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent>
          <DialogClose onClose={() => setIsDetailsOpen(false)} />
          <DialogHeader>
            <DialogTitle>Task Details</DialogTitle>
          </DialogHeader>

          {selectedTask && (
            <div className="space-y-4">
              {/* Basic Information */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Basic Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium">Task ID:</span>
                    <span className="font-mono">{selectedTask.task_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Status:</span>
                    {getStatusBadge(selectedTask.status)}
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium">Progress:</span>
                    <span>{selectedTask.progress.toFixed(1)}%</span>
                  </div>
                </CardContent>
              </Card>

              {/* Timing Information */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Timing Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium">Created at:</span>
                    <span>{new Date(selectedTask.created_at).toLocaleString()}</span>
                  </div>
                  {selectedTask.started_at && (
                    <div className="flex justify-between">
                      <span className="font-medium">Started at:</span>
                      <span>{new Date(selectedTask.started_at).toLocaleString()}</span>
                    </div>
                  )}
                  {selectedTask.completed_at && (
                    <div className="flex justify-between">
                      <span className="font-medium">Completed at:</span>
                      <span>{new Date(selectedTask.completed_at).toLocaleString()}</span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Status & Messages */}
              {(selectedTask.message || selectedTask.error) && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Status & Messages</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    {selectedTask.message && (
                      <div>
                        <p className="font-medium">Current message:</p>
                        <p className="text-blue-600">{selectedTask.message}</p>
                      </div>
                    )}
                    {selectedTask.error && (
                      <div>
                        <p className="font-medium text-red-600">Error:</p>
                        <p className="text-red-600">{selectedTask.error}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Metadata */}
              {selectedTask.metadata && Object.keys(selectedTask.metadata).length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Metadata</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
                      {JSON.stringify(selectedTask.metadata, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
