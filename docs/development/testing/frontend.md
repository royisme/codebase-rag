# Frontend Testing Guide

## Table of Contents

- [Overview](#overview)
- [Test Stack](#test-stack)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Types](#test-types)
- [Mocking Strategies](#mocking-strategies)
- [Coverage Requirements](#coverage-requirements)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Frontend testing for the Code Graph Web UI ensures component reliability, user interaction correctness, and integration with backend APIs. We use a modern testing stack optimized for React 18 and TypeScript applications.

### Testing Philosophy

- **User behavior testing**: Focus on what users see and do, not implementation details
- **Accessibility first**: Use semantic queries that mirror how users interact with the UI
- **Integration over isolation**: Test component interactions and API integrations
- **Fast feedback**: Keep unit tests fast, integration tests comprehensive
- **Regression prevention**: Maintain high coverage for critical user paths

## Test Stack

### Core Testing Framework

- **Vitest**: Fast unit test framework with Vite integration
- **React Testing Library**: Component testing utilities focused on user behavior
- **@testing-library/jest-dom**: Custom matchers for DOM assertions
- **@testing-library/user-event**: User interaction simulation
- **jsdom**: DOM environment for headless testing

### Additional Tools

- **MSW (Mock Service Worker)**: API mocking at network level
- **Vitest UI**: Interactive test runner and debugger
- **@vitest/coverage-v8**: Code coverage reporting
- **@testing-library/react**: React-specific testing utilities

## Test Organization

### Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/
│   │       ├── button.tsx
│   │       ├── button.test.tsx          # Component tests
│   │       ├── badge.tsx
│   │       └── badge.test.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── api.test.ts                  # API layer tests
│   │   ├── utils.ts
│   │   └── utils.test.ts                # Utility function tests
│   ├── test/
│   │   ├── setup.ts                     # Test configuration
│   │   ├── mocks.ts                     # Global mocks
│   │   └── fixtures.ts                  # Test data fixtures
│   └── routes/
│       ├── index.tsx
│       ├── index.test.tsx               # Page-level tests
│       └── tasks.tsx
├── vitest.config.ts                     # Vitest configuration
└── package.json
```

### Test File Naming

- **Unit tests**: `*.test.ts` or `*.test.tsx`
- **Integration tests**: `*.integration.test.ts` or `*.integration.test.tsx`
- **E2E tests**: `*.e2e.test.ts` (if added in future)
- **Test utilities**: `test/*.ts` (helpers, fixtures, mocks)

## Running Tests

### Development Mode

```bash
# Install dependencies
npm install

# Run tests in watch mode (recommended for development)
npm test

# Run tests once
npm run test

# Run tests with UI interface
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### CI/CD Mode

```bash
# Run tests with coverage reporting
npm run test:coverage

# Run tests without watch (CI environment)
CI=true npm run test
```

### Test Filtering

```bash
# Run specific test file
npm test button.test.tsx

# Run tests matching pattern
npm test -- --grep "Button"

# Run tests excluding pattern
npm test -- --grep "!Button"

# Run only changed files (if using git)
npm test -- --changed
```

## Writing Tests

### Component Testing Example

```typescript
// src/components/ui/button.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './button'

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('handles click events', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(<Button onClick={handleClick}>Click me</Button>)
    await user.click(screen.getByRole('button'))

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('applies variant styles correctly', () => {
    render(<Button variant="destructive">Delete</Button>)
    const button = screen.getByRole('button', { name: 'Delete' })
    expect(button).toHaveClass('bg-destructive')
  })

  it('is accessible via keyboard', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(<Button onClick={handleClick}>Submit</Button>)
    const button = screen.getByRole('button')

    await user.tab() // Focus button
    expect(button).toHaveFocus()

    await user.keyboard('{Enter}')
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
```

### Page-Level Testing Example

```typescript
// src/routes/tasks.test.tsx
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from '@tanstack/react-router'
import { taskApi } from '../lib/api'
import { TasksRoute } from './tasks'

// Mock API
vi.mock('../lib/api')
const mockTaskApi = vi.mocked(taskApi)

describe('Tasks Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('displays loading state initially', () => {
    mockTaskApi.listTasks.mockImplementation(() => new Promise(() => {}))

    renderTasksPage()
    expect(screen.getByText('Loading tasks...')).toBeInTheDocument()
  })

  it('displays tasks when loaded', async () => {
    const mockTasks = {
      tasks: [
        { id: '1', status: 'completed', progress: 100, created_at: '2024-01-01' },
        { id: '2', status: 'processing', progress: 50, created_at: '2024-01-02' }
      ],
      total_count: 2
    }

    mockTaskApi.listTasks.mockResolvedValue(mockTasks)

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Task #1')).toBeInTheDocument()
      expect(screen.getByText('Task #2')).toBeInTheDocument()
    })
  })

  it('filters tasks by status', async () => {
    const user = userEvent.setup()
    const mockTasks = {
      tasks: [{ id: '1', status: 'processing', progress: 50 }],
      total_count: 1
    }

    mockTaskApi.listTasks.mockResolvedValue(mockTasks)

    renderTasksPage()

    // Wait for initial load
    await waitFor(() => screen.getByText('Task #1'))

    // Filter by processing status
    const statusFilter = screen.getByLabelText('Filter by status')
    await user.selectOptions(statusFilter, 'processing')

    expect(mockTaskApi.listTasks).toHaveBeenCalledWith({ status: 'processing' })
  })
})

function renderTasksPage() {
  const router = createMemoryRouter([
    {
      path: '/tasks',
      element: <TasksRoute.Component />
    }
  ], {
    initialEntries: ['/tasks']
  })

  return render(
    <RouterProvider router={router} />
  )
}
```

### Utility Function Testing

```typescript
// src/lib/utils.test.ts
import { describe, it, expect } from 'vitest'
import { formatBytes, formatDate, cn } from './utils'

describe('formatBytes', () => {
  it('formats bytes correctly', () => {
    expect(formatBytes(0)).toBe('0 Bytes')
    expect(formatBytes(1024)).toBe('1.0 KB')
    expect(formatBytes(1048576)).toBe('1.0 MB')
    expect(formatBytes(1073741824)).toBe('1.0 GB')
  })

  it('handles edge cases', () => {
    expect(formatBytes(-1)).toBe('0 Bytes')
    expect(formatBytes(NaN)).toBe('0 Bytes')
    expect(formatBytes(Infinity)).toBe('Infinity Bytes')
  })
})

describe('formatDate', () => {
  it('formats dates in relative time', () => {
    const now = new Date()
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)

    expect(formatDate(oneHourAgo)).toMatch(/hour ago/)
  })
})

describe('cn utility', () => {
  it('merges class names correctly', () => {
    expect(cn('btn', 'btn-primary')).toBe('btn btn-primary')
    expect(cn('btn', null && 'hidden')).toBe('btn')
    expect(cn('btn', { 'active': true })).toBe('btn active')
  })
})
```

## Test Types

### Unit Tests

**Purpose**: Test individual functions, components, or modules in isolation

**Characteristics**:
- Fast execution (< 100ms per test)
- No external dependencies
- Predictable results
- Easy to debug

**Examples**:
- Utility functions (`formatBytes`, `cn`)
- Pure components (`Button`, `Badge`)
- Custom hooks (`useTaskStatus`)

### Integration Tests

**Purpose**: Test how multiple parts work together

**Characteristics**:
- Test component interactions
- Include API integrations
- Test user workflows
- More realistic than unit tests

**Examples**:
- Page-level functionality
- Form submissions
- Data fetching workflows
- Navigation flows

### Visual Regression Tests

**Purpose**: Prevent unintended UI changes

**Tools** (can be added later):
- Chromatic
- Storybook
- Percy

### E2E Tests

**Purpose**: Test complete user journeys

**Tools** (can be added later):
- Playwright
- Cypress

## Mocking Strategies

### API Mocking with MSW

```typescript
// src/test/mocks/handlers.ts
import { rest } from 'msw'
import { setupServer } from 'msw/node'

export const handlers = [
  // Mock task API
  rest.get('/api/v1/tasks', (req, res, ctx) => {
    const status = req.url.searchParams.get('status')

    const mockTasks = [
      { id: '1', status: 'completed', progress: 100 },
      { id: '2', status: 'processing', progress: 50 }
    ]

    const filteredTasks = status
      ? mockTasks.filter(task => task.status === status)
      : mockTasks

    return res(
      ctx.status(200),
      ctx.json({ tasks: filteredTasks, total_count: filteredTasks.length })
    )
  }),

  // Mock repository API
  rest.post('/api/v1/repositories/ingest', (req, res, ctx) => {
    return res(
      ctx.status(202),
      ctx.json({ task_id: 'mock-task-123' })
    )
  })
]

export const server = setupServer(...handlers)
```

### Component Mocking

```typescript
// Mock Recharts components for testing
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />
}))
```

### Local Storage Mocking

```typescript
// src/test/mocks/storage.ts
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

beforeEach(() => {
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock
  })
})
```

## Coverage Requirements

### Target Metrics

- **Components**: 80%+ line coverage
- **Utilities**: 90%+ line coverage
- **API Layer**: 85%+ line coverage
- **Overall**: 75%+ line coverage

### Coverage Configuration

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        'dist/'
      ],
      thresholds: {
        global: {
          branches: 70,
          functions: 75,
          lines: 75,
          statements: 75
        }
      }
    }
  }
})
```

### Coverage Reports

```bash
# Generate coverage report
npm run test:coverage

# View HTML report
open coverage/index.html

# Check specific file coverage
npm run test:coverage -- src/components/ui/button.tsx
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests

on:
  push:
    branches: [ main, develop ]
    paths: [ 'frontend/**' ]
  pull_request:
    branches: [ main ]
    paths: [ 'frontend/**' ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Install dependencies
      run: |
        cd frontend
        npm ci

    - name: Run tests
      run: |
        cd frontend
        npm run test:coverage

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./frontend/coverage/lcov.info
        flags: frontend
```

### Pre-commit Hooks

```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged"
    }
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "npm run test:related --",
      "npm run lint:fix"
    ]
  }
}
```

## Best Practices

### 1. Test User Behavior, Not Implementation

✅ **Good**: Test what users see and do
```typescript
expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
await user.click(screen.getByRole('button'))
```

❌ **Bad**: Test internal state or DOM structure
```typescript
expect(component.state.isSubmitting).toBe(true)
expect(wrapper.find('.btn-primary').length).toBe(1)
```

### 2. Use Accessible Queries

Priority order (React Testing Library recommendations):

1. **getByRole()** - Best for accessibility
2. **getByLabelText()** - For form inputs
3. **getByPlaceholderText()** - For inputs without labels
4. **getByText()** - For non-interactive text content
5. **getByTestId()** - Last resort, for non-interactive elements

### 3. Keep Tests Isolated

```typescript
beforeEach(() => {
  vi.clearAllMocks()  // Clear mock calls
  localStorage.clear()  // Reset storage
})

afterEach(() => {
  cleanup()  // Cleanup DOM
})
```

### 4. Test Error States

```typescript
it('displays error message when API fails', async () => {
  mockTaskApi.listTasks.mockRejectedValue(new Error('Network error'))

  renderTasksPage()

  await waitFor(() => {
    expect(screen.getByText(/failed to load tasks/i)).toBeInTheDocument()
  })
})
```

### 5. Use Test Fixtures

```typescript
// src/test/fixtures/tasks.ts
export const mockTasks = {
  completed: {
    id: '1',
    status: 'completed' as const,
    progress: 100,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T01:00:00Z'
  },
  processing: {
    id: '2',
    status: 'processing' as const,
    progress: 50,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:30:00Z'
  }
}

// Usage in tests
it('displays task status correctly', async () => {
  mockTaskApi.listTasks.mockResolvedValue({
    tasks: [mockTasks.completed, mockTasks.processing],
    total_count: 2
  })

  // ... test implementation
})
```

### 6. Test Loading States

```typescript
it('shows loading spinner while fetching', () => {
  mockTaskApi.listTasks.mockImplementation(() => new Promise(() => {}))

  renderTasksPage()

  expect(screen.getByRole('progressbar')).toBeInTheDocument()
  expect(screen.getByText('Loading tasks...')).toBeInTheDocument()
})
```

### 7. Use Data-testid Wisely

Only use `data-testid` when elements can't be identified by accessible queries:

```typescript
// Component
<div data-testid="task-progress-bar" />

// Test
expect(screen.getByTestId('task-progress-bar')).toHaveAttribute('aria-valuenow', '50')
```

## Troubleshooting

### Common Issues

#### Tests Failing with "Not Found" Errors

```bash
# Error: Testing library element not found
# Solution: Use waitFor for async operations

await waitFor(() => {
  expect(screen.getByText('Expected text')).toBeInTheDocument()
})
```

#### Mock Functions Not Being Called

```typescript
// Ensure you're using vi.mocked() for TypeScript
const mockApi = vi.mocked(taskApi)

// Check that the mock is being called with correct arguments
expect(mockApi.listTasks).toHaveBeenCalledWith({ status: 'processing' })
```

#### Act() Warnings

```typescript
// Wrap user interactions in act() when they cause state updates
import { act } from 'react-dom/test-utils'

await act(async () => {
  await user.click(screen.getByRole('button'))
})
```

#### Memory Leaks in Tests

```typescript
// Clean up timers and subscriptions
afterEach(() => {
  vi.clearAllTimers()
  cleanup()
})
```

### Debugging Tests

#### Using Vitest UI

```bash
npm run test:ui
```

#### Console Logging

```typescript
// Add debugging to tests
screen.debug()  // Prints current DOM
screen.debug(screen.getByTestId('task-item'))  // Prints specific element
```

#### Test Filtering

```bash
# Run only failing tests
npm test -- --reporter=verbose

# Run tests in specific file
npm test button.test.tsx

# Run tests matching pattern
npm test -- --grep "should handle"
```

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [MSW Documentation](https://mswjs.io/)
- [TanStack Router Testing](https://tanstack.com/router/latest/docs/framework/react/guide/testing)

## Next Steps

- **Backend Testing**: See [Testing Overview](../testing.md) for backend testing practices
- **API Documentation**: Understand the APIs your frontend tests should mock
- **Component Library**: Learn about reusable UI components and their testing patterns
- **Performance Testing**: Consider adding performance testing for critical user paths