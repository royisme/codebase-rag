import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { taskApi, healthApi } from './api'

// Mock axios
vi.mock('axios')
const mockedAxios = axios as any

describe('API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('taskApi', () => {
    it('should list tasks', async () => {
      const mockTasks = {
        tasks: [
          {
            task_id: '123',
            status: 'success',
            progress: 100,
            message: 'Done',
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total_count: 1,
      }

      mockedAxios.create.mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockTasks }),
      } as any)

      const result = await taskApi.listTasks({ limit: 10 })
      expect(result.data).toEqual(mockTasks)
    })

    it('should get task status', async () => {
      const mockTask = {
        task_id: '123',
        status: 'running',
        progress: 50,
        message: 'Processing...',
        created_at: '2024-01-01T00:00:00Z',
      }

      mockedAxios.create.mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockTask }),
      } as any)

      const result = await taskApi.getStatus('123')
      expect(result.data).toEqual(mockTask)
    })

    it('should cancel task', async () => {
      mockedAxios.create.mockReturnValue({
        post: vi.fn().mockResolvedValue({ data: { success: true } }),
      } as any)

      const result = await taskApi.cancelTask('123')
      expect(result.data).toEqual({ success: true })
    })
  })

  describe('healthApi', () => {
    it('should check health', async () => {
      const mockHealth = {
        status: 'healthy',
        services: { neo4j: true },
        version: '1.0.0',
      }

      mockedAxios.create.mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockHealth }),
      } as any)

      const result = await healthApi.check()
      expect(result.data).toEqual(mockHealth)
    })
  })
})
