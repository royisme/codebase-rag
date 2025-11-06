import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { healthApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, Database, Server, CheckCircle2, AlertCircle } from 'lucide-react'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

function Dashboard() {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.check().then(res => res.data),
    refetchInterval: 5000,
  })

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  const isHealthy = health?.status === 'healthy'
  const services = health?.services || {}

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor your code graph knowledge system
        </p>
      </div>

      {/* System Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>System Status</CardTitle>
              <CardDescription>Overall system health and services</CardDescription>
            </div>
            <Badge variant={isHealthy ? 'success' : 'destructive'} className="text-sm">
              {isHealthy ? (
                <>
                  <CheckCircle2 className="w-4 h-4 mr-1" />
                  Healthy
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 mr-1" />
                  Degraded
                </>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {/* Neo4j Service */}
            <div className="flex items-center space-x-4 p-4 border rounded-lg">
              <div className={`p-3 rounded-full ${services.neo4j_knowledge_service ? 'bg-green-100' : 'bg-red-100'}`}>
                <Database className={`w-6 h-6 ${services.neo4j_knowledge_service ? 'text-green-600' : 'text-red-600'}`} />
              </div>
              <div>
                <p className="text-sm font-medium">Neo4j Knowledge</p>
                <p className="text-xs text-muted-foreground">
                  {services.neo4j_knowledge_service ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>

            {/* Graph Service */}
            <div className="flex items-center space-x-4 p-4 border rounded-lg">
              <div className={`p-3 rounded-full ${services.graph_service ? 'bg-green-100' : 'bg-red-100'}`}>
                <Activity className={`w-6 h-6 ${services.graph_service ? 'text-green-600' : 'text-red-600'}`} />
              </div>
              <div>
                <p className="text-sm font-medium">Graph Service</p>
                <p className="text-xs text-muted-foreground">
                  {services.graph_service ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>

            {/* Task Queue */}
            <div className="flex items-center space-x-4 p-4 border rounded-lg">
              <div className={`p-3 rounded-full ${services.task_queue ? 'bg-green-100' : 'bg-red-100'}`}>
                <Server className={`w-6 h-6 ${services.task_queue ? 'text-green-600' : 'text-red-600'}`} />
              </div>
              <div>
                <p className="text-sm font-medium">Task Queue</p>
                <p className="text-xs text-muted-foreground">
                  {services.task_queue ? 'Running' : 'Stopped'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Links */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="hover:bg-accent cursor-pointer transition-colors">
          <CardHeader>
            <CardTitle className="text-lg">View Tasks</CardTitle>
            <CardDescription>Monitor processing tasks and queue status</CardDescription>
          </CardHeader>
        </Card>

        <Card className="hover:bg-accent cursor-pointer transition-colors">
          <CardHeader>
            <CardTitle className="text-lg">Manage Repositories</CardTitle>
            <CardDescription>Ingest and manage code repositories</CardDescription>
          </CardHeader>
        </Card>

        <Card className="hover:bg-accent cursor-pointer transition-colors">
          <CardHeader>
            <CardTitle className="text-lg">View Metrics</CardTitle>
            <CardDescription>System performance and statistics</CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Version Info */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Version: {health?.version || '0.6.0'}</span>
            <span>Last updated: {new Date().toLocaleString()}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
