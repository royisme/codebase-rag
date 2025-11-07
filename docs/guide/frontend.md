# Web User Interface

## Introduction

The Code Graph Knowledge System provides a modern, responsive **Web UI** for human users to monitor and interact with the system. Built with React 18, TypeScript, and shadcn/ui components, the Web UI offers real-time monitoring capabilities and an intuitive interface for managing your knowledge graph operations.

The Web UI runs on **Port 8080** as part of the dual-server architecture, complementing the MCP service (Port 8000) and REST API.

## What is the Web UI?

The Web UI is a browser-based interface that provides:

- **Real-time system monitoring** with live updates
- **Task management** for long-running operations
- **Repository ingestion** controls and progress tracking
- **Metrics visualization** with interactive charts
- **Responsive design** for desktop and mobile devices

Unlike the MCP protocol (for AI assistants) and REST API (for programs), the Web UI is specifically designed for **human interaction** with visual feedback and intuitive controls.

## Key Features

### 1. Real-time Dashboard

Monitor system health and status at a glance:

- **Service Connectivity**: Check Neo4j, embedding service, and LLM availability
- **System Statistics**: View node counts, relationship counts, and database size
- **Quick Actions**: Direct links to common operations
- **Auto-refresh**: Health checks every 5 seconds

### 2. Task Monitoring

Track long-running operations with detailed progress:

- **Live Progress Bars**: Visual indicators for file processing
- **Status Filtering**: View tasks by status (pending, processing, completed, failed)
- **Task Details**: Error messages, timing information, and operation context
- **Auto-refresh**: Task status updates every 3 seconds

### 3. Repository Management

Ingest and manage code repositories:

- **Multiple Sources**: Git URLs, local paths, or file uploads
- **Language Detection**: Automatic identification of 15+ programming languages
- **Ingestion Modes**: Full or incremental processing
- **Progress Tracking**: Real-time feedback during large repository processing

### 4. Metrics Visualization

Monitor system performance and usage:

- **Neo4j Statistics**: Database metrics, query performance, index usage
- **Operation Metrics**: Task completion rates, processing times
- **Resource Monitoring**: Memory usage, storage consumption
- **Interactive Charts**: Recharts-based visualizations with filtering options

## Accessing the Web UI

### Production Deployment

When you start the complete system:

```bash
python start.py
```

The Web UI is available at: **http://localhost:8080**

!!! info "Dual-Server Architecture"
    The system runs two servers simultaneously:

    - **Port 8000**: MCP SSE Service + REST API
    - **Port 8080**: Web UI + REST API

    Both servers share the same REST API endpoints.

### Development Mode

For frontend development:

```bash
cd frontend
npm install
npm run dev
```

Development server: **http://localhost:3000**
API proxy: `http://localhost:8000` (configured automatically)

## User Interface Overview

### Navigation Structure

```
┌─────────────────────────────────────────┐
│ Code Graph Knowledge System             │
├─────────────────────────────────────────┤
│ Dashboard  Tasks  Repositories  Metrics │
├─────────────────────────────────────────┤
│                                         │
│              Main Content               │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

### Pages and Features

#### Dashboard (`/`)
- System health indicators
- Quick action buttons
- Recent task summary
- Database statistics

#### Tasks (`/tasks`)
- Active task monitoring
- Historical task list
- Status filtering
- Error details and troubleshooting

#### Repositories (`/repositories`)
- Repository ingestion form
- Language selection options
- Progress tracking
- Batch operations

#### Metrics (`/metrics`)
- Interactive charts
- Time range filtering
- Metric type selection
- Raw data export

## Technology Stack

### Core Technologies

- **React 18**: Modern UI library with hooks and concurrent features
- **TypeScript**: Type safety and better developer experience
- **Vite**: Fast build tool and development server
- **TanStack Router**: Type-safe routing with code splitting

### UI Framework

- **shadcn/ui**: Beautiful, accessible component library
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Consistent icon system
- **Recharts**: Declarative chart library

### Data Management

- **TanStack Query**: Server state management and caching
- **Axios**: HTTP client with request/response interceptors
- **React Hook Form**: Form validation and management

## Responsive Design

The Web UI is fully responsive and works across devices:

| Device | Screen Width | Layout |
|--------|--------------|--------|
| Desktop | 1280px+ | Full multi-column layout |
| Laptop | 1024px-1279px | Optimized two-column layout |
| Tablet | 768px-1023px | Single column with navigation |
| Mobile | 320px-767px | Compact mobile layout |

## Real-time Updates

### Update Frequencies

- **Dashboard Health**: Every 5 seconds
- **Task Status**: Every 3 seconds
- **Metrics Data**: Every 10 seconds
- **Repository Progress**: Real-time during ingestion

### WebSocket Connections

For critical operations, the Web UI uses WebSocket connections to provide instant updates:

```typescript
// Example: Real-time task updates
const ws = new WebSocket('ws://localhost:8080/ws/tasks')
ws.onmessage = (event) => {
  const taskUpdate = JSON.parse(event.data)
  updateTaskStatus(taskUpdate)
}
```

## Integration with System Architecture

### Data Flow

```
User Action → Web UI → REST API → Backend Service → Neo4j
    ↑                                                    ↓
Real-time Updates ← SSE/WebSocket ← Task Queue ← Background Processing
```

### Shared REST API

The Web UI consumes the same REST API used by external applications:

- **Tasks API**: Monitor and manage background operations
- **Repositories API**: Ingest and query repository data
- **Metrics API**: Access system performance data
- **Health API**: Check system status and connectivity

## Configuration

### Environment Variables

The Web UI doesn't require additional environment variables. It inherits configuration from the backend:

```bash
# Backend configuration (automatically shared)
WEB_UI_PORT=8080
API_BASE_URL=http://localhost:8000
```

### Custom Configuration

For advanced customization, you can modify `frontend/src/config.ts`:

```typescript
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  refreshInterval: {
    dashboard: 5000,    // 5 seconds
    tasks: 3000,        // 3 seconds
    metrics: 10000      // 10 seconds
  }
}
```

## Troubleshooting

### Common Issues

#### API Connection Problems

!!! error "Connection Failed"
    If the Web UI can't connect to the backend:

    1. **Check backend status**: `curl http://localhost:8000/api/v1/health`
    2. **Verify port configuration**: Ensure ports 8000 and 8080 are available
    3. **Check browser console**: Look for CORS or network errors
    4. **Refresh the page**: Sometimes a simple refresh resolves connection issues

#### Real-time Updates Not Working

!!! warning "WebSocket Issues"
    If real-time updates stop working:

    1. **Check network connection**: WebSocket requires stable connection
    2. **Disable browser extensions**: Some ad-blockers interfere with WebSockets
    3. **Clear browser cache**: Old cached scripts might cause conflicts
    4. **Restart servers**: Try restarting both backend services

#### Performance Issues

!!! tip "Optimization Tips"
    For better performance with large datasets:

    1. **Use filters**: Apply date and status filters to reduce data
    2. **Limit batch sizes**: Process repositories in smaller chunks
    3. **Close unused tabs**: Multiple tabs can compete for resources
    4. **Check system resources**: Monitor memory and CPU usage

## Development and Customization

### Adding New Pages

1. **Create route file**:
```typescript
// frontend/src/routes/my-feature.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/my-feature')({
  component: MyFeature,
})
```

2. **Create component**:
```typescript
function MyFeature() {
  return <div>My New Feature</div>
}
```

3. **Add navigation**:
Update `frontend/src/routes/__root.tsx` to include the new page in navigation.

### Customizing UI Components

The Web UI uses shadcn/ui components which can be customized:

```bash
# Add new components
cd frontend
npx shadcn-ui@latest add [component-name]

# Customize existing components
# Edit: frontend/src/components/ui/[component].tsx
```

## Next Steps

- **Repository Management**: Learn how to ingest and manage code repositories
- **Task Monitoring**: Understand task processing and troubleshooting
- **API Integration**: Explore REST API endpoints for custom integrations
- **Architecture Overview**: Understand the complete system design

For technical implementation details, see [Frontend Testing Guide](../development/testing/frontend.md).