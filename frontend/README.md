# Code Graph Knowledge System - Frontend

Modern React frontend with shadcn UI and TanStack Router for the Code Graph Knowledge System.

## Features

- **Dashboard**: System health monitoring and quick links
- **Tasks**: Real-time task monitoring with progress tracking
- **Repositories**: Repository ingestion and management
- **Metrics**: Prometheus metrics visualization

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TanStack Router** - Type-safe routing
- **TanStack Query** - Data fetching and caching
- **shadcn/ui** - Beautiful UI components
- **Tailwind CSS** - Utility-first CSS
- **Recharts** - Chart library
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install
# or
bun install
```

### Development

```bash
# Start dev server
npm run dev
# or
bun dev

# Frontend will be available at http://localhost:3000
# API proxy configured to http://localhost:8000
```

### Build

```bash
# Build for production
npm run build
# or
bun run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/           # shadcn UI components
│   ├── lib/
│   │   ├── api.ts        # API client and types
│   │   └── utils.ts      # Utility functions
│   ├── routes/
│   │   ├── __root.tsx    # Root layout with navigation
│   │   ├── index.tsx     # Dashboard page
│   │   ├── tasks.tsx     # Tasks monitoring page
│   │   ├── repositories.tsx  # Repository management
│   │   └── metrics.tsx   # Metrics visualization
│   ├── index.css         # Global styles with Tailwind
│   └── main.tsx          # Application entry point
├── public/               # Static assets
├── index.html            # HTML entry point
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript config
├── vite.config.ts        # Vite config
├── tailwind.config.js    # Tailwind config
└── postcss.config.js     # PostCSS config
```

## Key Features

### Real-time Updates

- Tasks page auto-refreshes every 3 seconds
- Dashboard health check updates every 5 seconds
- Metrics refresh every 10 seconds

### API Integration

All API calls are proxied through Vite dev server:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Proxy: `/api/*` → `http://localhost:8000/api/*`

### Responsive Design

Fully responsive layout that works on:
- Desktop (1920px+)
- Laptop (1280px+)
- Tablet (768px+)
- Mobile (320px+)

### Type Safety

- Full TypeScript support
- Type-safe routing with TanStack Router
- API types defined in `lib/api.ts`

## Available Pages

### Dashboard (`/`)
- System health status
- Service connectivity
- Quick navigation links

### Tasks (`/tasks`)
- Real-time task monitoring
- Progress bars for running tasks
- Status filtering
- Task history

### Repositories (`/repositories`)
- Repository ingestion form
- Support for Git URLs and local paths
- Full and incremental modes
- Multi-language support (Python, TS, JS, Java, PHP, Go)

### Metrics (`/metrics`)
- Prometheus metrics visualization
- Neo4j statistics
- Graph operation metrics
- Raw metrics view

## Development

### Adding New Pages

1. Create a new file in `src/routes/`:
```tsx
// src/routes/my-page.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/my-page')({
  component: MyPage,
})

function MyPage() {
  return <div>My Page</div>
}
```

2. Add navigation link in `src/routes/__root.tsx`

### Adding New Components

1. Create component in `src/components/`:
```tsx
// src/components/MyComponent.tsx
export function MyComponent() {
  return <div>My Component</div>
}
```

2. Import and use in pages

### Adding shadcn Components

```bash
# Use shadcn CLI to add components
npx shadcn-ui@latest add [component-name]
```

## Environment Variables

No environment variables needed for frontend. Backend URL is configured in `vite.config.ts` proxy settings.

## Production Deployment

### Static Hosting

```bash
# Build
npm run build

# Deploy dist/ folder to:
# - Vercel
# - Netlify
# - GitHub Pages
# - Any static hosting
```

### Docker

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Port Already in Use

```bash
# Change port in vite.config.ts
server: {
  port: 3001,  # Use different port
}
```

### API Connection Issues

1. Check backend is running: `curl http://localhost:8000/api/v1/health`
2. Check proxy configuration in `vite.config.ts`
3. Check browser console for CORS errors

### Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Contributing

1. Follow existing code style
2. Use TypeScript for all new files
3. Add types for API responses
4. Test on multiple screen sizes
5. Update this README for new features

## License

Same as parent project
