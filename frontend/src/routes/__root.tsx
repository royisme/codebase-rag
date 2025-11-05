import { createRootRouteWithContext, Link, Outlet } from '@tanstack/react-router'
import { QueryClient } from '@tanstack/react-query'
import { Activity, Database, Home, ListTodo } from 'lucide-react'

interface RouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
})

function RootComponent() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <h1 className="text-xl font-bold">Code Graph System</h1>
              <div className="flex space-x-1">
                <Link
                  to="/"
                  className="px-3 py-2 rounded-md text-sm font-medium hover:bg-accent [&.active]:bg-accent"
                >
                  <Home className="inline-block w-4 h-4 mr-2" />
                  Dashboard
                </Link>
                <Link
                  to="/tasks"
                  className="px-3 py-2 rounded-md text-sm font-medium hover:bg-accent [&.active]:bg-accent"
                >
                  <ListTodo className="inline-block w-4 h-4 mr-2" />
                  Tasks
                </Link>
                <Link
                  to="/repositories"
                  className="px-3 py-2 rounded-md text-sm font-medium hover:bg-accent [&.active]:bg-accent"
                >
                  <Database className="inline-block w-4 h-4 mr-2" />
                  Repositories
                </Link>
                <Link
                  to="/metrics"
                  className="px-3 py-2 rounded-md text-sm font-medium hover:bg-accent [&.active]:bg-accent"
                >
                  <Activity className="inline-block w-4 h-4 mr-2" />
                  Metrics
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
