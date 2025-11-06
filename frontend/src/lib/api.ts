import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Types
export interface HealthStatus {
  status: string
  services: Record<string, boolean>
  version: string
}

export interface TaskResult {
  files_processed?: number
  nodes_created?: number
  relationships_created?: number
  duration_ms?: number
  [key: string]: unknown
}

export interface TaskMetadata {
  repo_url?: string
  local_path?: string
  mode?: string
  file_count?: number
  [key: string]: unknown
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  progress: number
  message: string
  created_at: string
  started_at?: string
  completed_at?: string
  result?: TaskResult
  error?: string
  metadata?: TaskMetadata
}

export interface IngestRepoRequest {
  repo_url?: string
  local_path?: string
  branch?: string
  mode: 'full' | 'incremental'
  include_globs?: string[]
  exclude_globs?: string[]
  since_commit?: string
}

export interface IngestRepoResponse {
  task_id: string
  status: string
  message?: string
  files_processed?: number
  mode?: string
  changed_files_count?: number
}

export interface NodeSummary {
  type: string
  ref: string
  path?: string
  lang?: string
  score: number
  summary: string
}

export interface RelatedResponse {
  nodes: NodeSummary[]
  query: string
  repo_id: string
}

export interface ImpactNode {
  type: string
  path: string
  lang?: string
  repoId: string
  relationship: string
  depth: number
  score: number
  ref: string
  summary: string
}

export interface ImpactResponse {
  nodes: ImpactNode[]
  file: string
  repo_id: string
  depth: number
}

export interface ContextItemExtra {
  path?: string
  lang?: string
  score?: number
  [key: string]: unknown
}

export interface ContextItem {
  kind: string
  title: string
  summary: string
  ref: string
  extra?: ContextItemExtra
}

export interface ContextPack {
  items: ContextItem[]
  budget_used: number
  budget_limit: number
  stage: string
  repo_id: string
  category_counts?: Record<string, number>
}

// API Methods
export const healthApi = {
  check: () => api.get<HealthStatus>('/health'),
  metrics: () => api.get('/metrics', { responseType: 'text' }),
}

export const ingestApi = {
  ingestRepo: (data: IngestRepoRequest) =>
    api.post<IngestRepoResponse>('/ingest/repo', data),
}

export const graphApi = {
  getRelated: (params: { query: string; repoId: string; limit?: number }) =>
    api.get<RelatedResponse>('/graph/related', { params }),

  getImpact: (params: { repoId: string; file: string; depth?: number; limit?: number }) =>
    api.get<ImpactResponse>('/graph/impact', { params }),
}

export const contextApi = {
  getPack: (params: {
    repoId: string
    stage?: string
    budget?: number
    keywords?: string
    focus?: string
  }) => api.get<ContextPack>('/context/pack', { params }),
}

export interface ProcessDocumentRequest {
  content: string
  filename?: string
  document_type?: string
}

export interface ProcessDocumentResponse {
  task_id: string
  status: string
  message: string
}

export interface ProcessDirectoryRequest {
  directory_path: string
  file_patterns?: string[]
  recursive?: boolean
}

export interface ProcessDirectoryResponse {
  task_id: string
  status: string
  message: string
  files_found?: number
}

export const taskApi = {
  getStatus: (taskId: string) =>
    api.get<TaskStatus>(`/tasks/${taskId}`),

  listTasks: (params?: { status?: string; limit?: number }) =>
    api.get<{ tasks: TaskStatus[]; total_count: number }>('/tasks', { params }),

  cancelTask: (taskId: string) =>
    api.post(`/tasks/${taskId}/cancel`),

  processDocument: (data: ProcessDocumentRequest) =>
    api.post<ProcessDocumentResponse>('/documents/process', data),

  processDirectory: (data: ProcessDirectoryRequest) =>
    api.post<ProcessDirectoryResponse>('/documents/process-directory', data),
}

export default api
