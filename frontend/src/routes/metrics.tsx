import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { healthApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, TrendingUp, Database, Clock } from 'lucide-react'

export const Route = createFileRoute('/metrics')({
  component: MetricsPage,
})

function MetricsPage() {
  const { data: metricsText, isLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => healthApi.metrics().then(res => res.data),
    refetchInterval: 10000,
  })

  // Parse Prometheus metrics
  const parseMetrics = (text: string) => {
    const lines = text.split('\n')
    const metrics: Record<string, any> = {}

    lines.forEach(line => {
      if (line.startsWith('#') || !line.trim()) return

      const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^}]+\})?) (.+)$/)
      if (match) {
        const [, name, value] = match
        const baseName = name.split('{')[0]
        if (!metrics[baseName]) {
          metrics[baseName] = []
        }
        metrics[baseName].push({
          full: name,
          value: parseFloat(value),
        })
      }
    })

    return metrics
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  const metrics = metricsText ? parseMetrics(metricsText) : {}

  // Extract key metrics
  const getMetricValue = (name: string) => {
    const metric = metrics[name]
    if (!metric || metric.length === 0) return 0
    return metric[0].value || 0
  }

  const getMetricSum = (name: string) => {
    const metric = metrics[name]
    if (!metric) return 0
    return metric.reduce((sum, m) => sum + (m.value || 0), 0)
  }

  const neo4jConnected = getMetricValue('neo4j_connected')
  const totalRequests = getMetricSum('http_requests_total')
  const totalRepoIngestions = getMetricSum('repo_ingestion_total')
  const totalFilesIngested = getMetricSum('files_ingested_total')
  const totalGraphQueries = getMetricSum('graph_queries_total')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Metrics</h1>
        <p className="text-muted-foreground">
          System performance and statistics
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription>Neo4j Status</CardDescription>
              <Database className="w-4 h-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {neo4jConnected === 1 ? (
                <span className="text-green-600">Connected</span>
              ) : (
                <span className="text-red-600">Disconnected</span>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription>Total Requests</CardDescription>
              <Activity className="w-4 h-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRequests.toFixed(0)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              HTTP requests processed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription>Repositories</CardDescription>
              <TrendingUp className="w-4 h-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRepoIngestions.toFixed(0)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Total ingestions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription>Files Ingested</CardDescription>
              <Clock className="w-4 h-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalFilesIngested.toFixed(0)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Code files processed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Graph Operations */}
      <Card>
        <CardHeader>
          <CardTitle>Graph Operations</CardTitle>
          <CardDescription>Query and analysis statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Total Graph Queries</span>
              <span className="text-2xl font-bold">{totalGraphQueries.toFixed(0)}</span>
            </div>

            {metrics['graph_queries_total'] && (
              <div className="space-y-2">
                {metrics['graph_queries_total'].map((m, idx) => {
                  const opMatch = m.full.match(/operation="([^"]+)"/)
                  const statusMatch = m.full.match(/status="([^"]+)"/)
                  return (
                    <div key={idx} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        {opMatch ? opMatch[1] : 'unknown'} ({statusMatch ? statusMatch[1] : 'unknown'})
                      </span>
                      <span className="font-medium">{m.value?.toFixed(0) || 0}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Neo4j Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>Neo4j Statistics</CardTitle>
          <CardDescription>Database nodes and relationships</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            {/* Nodes */}
            <div>
              <h4 className="text-sm font-medium mb-2">Nodes by Label</h4>
              <div className="space-y-2">
                {metrics['neo4j_nodes_total'] ? (
                  metrics['neo4j_nodes_total'].map((m, idx) => {
                    const labelMatch = m.full.match(/label="([^"]+)"/)
                    return (
                      <div key={idx} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {labelMatch ? labelMatch[1] : 'Unknown'}
                        </span>
                        <span className="font-medium">{m.value?.toFixed(0) || 0}</span>
                      </div>
                    )
                  })
                ) : (
                  <p className="text-sm text-muted-foreground">No data</p>
                )}
              </div>
            </div>

            {/* Relationships */}
            <div>
              <h4 className="text-sm font-medium mb-2">Relationships by Type</h4>
              <div className="space-y-2">
                {metrics['neo4j_relationships_total'] ? (
                  metrics['neo4j_relationships_total'].map((m, idx) => {
                    const typeMatch = m.full.match(/type="([^"]+)"/)
                    return (
                      <div key={idx} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {typeMatch ? typeMatch[1] : 'Unknown'}
                        </span>
                        <span className="font-medium">{m.value?.toFixed(0) || 0}</span>
                      </div>
                    )
                  })
                ) : (
                  <p className="text-sm text-muted-foreground">No data</p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Raw Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Raw Metrics</CardTitle>
          <CardDescription>Prometheus format metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="text-xs bg-muted p-4 rounded-md overflow-x-auto max-h-96">
            {metricsText}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}
