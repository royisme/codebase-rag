# Frontend Testing Guide

This project uses **Vitest** for unit and integration testing of React components.

## Test Stack

- **Vitest**: Fast unit test framework (Vite-native)
- **React Testing Library**: Component testing utilities
- **@testing-library/jest-dom**: Custom matchers for assertions
- **@testing-library/user-event**: User interaction simulation
- **jsdom**: DOM environment for testing

## Running Tests

```bash
# Install dependencies first
npm install

# Run tests in watch mode (recommended for development)
npm test

# Run tests once
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage report
npm run test:coverage
```

## Test Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/
│   │       ├── button.tsx
│   │       ├── button.test.tsx          # Component tests
│   │       ├── badge.tsx
│   │       ├── badge.test.tsx
│   │       └── ...
│   ├── lib/
│   │   ├── utils.ts
│   │   ├── utils.test.ts                # Utility function tests
│   │   ├── api.ts
│   │   └── api.test.ts                  # API tests
│   └── test/
│       └── setup.ts                     # Test setup file
├── vitest.config.ts                     # Vitest configuration
└── TEST.md                              # This file
```

## Writing Tests

### Component Test Example

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from './button'
import userEvent from '@testing-library/user-event'

describe('Button', () => {
  it('should render button with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('should handle click events', async () => {
    const user = userEvent.setup()
    let clicked = false

    render(<Button onClick={() => { clicked = true }}>Click me</Button>)
    await user.click(screen.getByRole('button'))

    expect(clicked).toBe(true)
  })
})
```

### Utility Function Test Example

```typescript
import { describe, it, expect } from 'vitest'
import { formatBytes } from './utils'

describe('formatBytes', () => {
  it('should format bytes correctly', () => {
    expect(formatBytes(0)).toBe('0 Bytes')
    expect(formatBytes(1024)).toBe('1 KB')
    expect(formatBytes(1024 * 1024)).toBe('1 MB')
  })
})
```

### API Test Example (with mocking)

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { taskApi } from './api'

vi.mock('axios')

describe('taskApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should list tasks', async () => {
    const mockTasks = { tasks: [], total_count: 0 }

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockTasks }),
    } as any)

    const result = await taskApi.listTasks()
    expect(result.data).toEqual(mockTasks)
  })
})
```

## Test Coverage

Run coverage report to see which parts of the code are tested:

```bash
npm run test:coverage
```

Coverage reports are generated in:
- Terminal: Summary view
- `coverage/index.html`: Detailed HTML report

### Coverage Targets

- **Components**: Aim for 80%+ coverage
- **Utils**: Aim for 90%+ coverage
- **API**: Aim for 70%+ coverage (mocked)

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    cd frontend
    npm install
    npm run test:coverage
```

## Best Practices

### 1. Test User Behavior, Not Implementation

✅ **Good**: Test what the user sees and does
```typescript
expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument()
await user.click(screen.getByRole('button'))
```

❌ **Bad**: Test internal state or implementation details
```typescript
expect(component.state.isClicked).toBe(true)
```

### 2. Use Accessible Queries

Priority order:
1. `getByRole()` - Best for accessibility
2. `getByLabelText()` - For form inputs
3. `getByPlaceholderText()` - For inputs without labels
4. `getByText()` - For text content
5. `getByTestId()` - Last resort

### 3. Keep Tests Isolated

Each test should be independent:
```typescript
beforeEach(() => {
  vi.clearAllMocks()  // Clear mocks
})

afterEach(() => {
  cleanup()  // Cleanup DOM
})
```

### 4. Mock External Dependencies

Mock API calls, timers, and third-party libraries:
```typescript
vi.mock('axios')
vi.mock('@tanstack/react-query')
```

### 5. Test Error States

Don't just test the happy path:
```typescript
it('should show error message when API fails', async () => {
  mockedApi.listTasks.mockRejectedValue(new Error('Network error'))

  render(<TasksList />)

  expect(await screen.findByText(/error/i)).toBeInTheDocument()
})
```

## Debugging Tests

### 1. Use `screen.debug()`

```typescript
it('should render component', () => {
  render(<MyComponent />)
  screen.debug()  // Prints DOM to console
})
```

### 2. Run Single Test

```bash
npm test -- button.test.tsx
```

### 3. Use Vitest UI

```bash
npm run test:ui
```

Opens a browser UI for interactive test debugging.

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
