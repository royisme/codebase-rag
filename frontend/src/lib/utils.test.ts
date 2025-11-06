import { describe, it, expect } from 'vitest'
import { cn, formatBytes, formatDuration, formatNumber } from './utils'

describe('utils', () => {
  describe('cn', () => {
    it('should merge class names', () => {
      expect(cn('foo', 'bar')).toBe('foo bar')
    })

    it('should handle conditional classes', () => {
      expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
    })

    it('should merge tailwind classes correctly', () => {
      expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
    })
  })

  describe('formatBytes', () => {
    it('should format 0 bytes', () => {
      expect(formatBytes(0)).toBe('0 Bytes')
    })

    it('should format bytes', () => {
      expect(formatBytes(1024)).toBe('1 KB')
    })

    it('should format kilobytes', () => {
      expect(formatBytes(1024 * 1024)).toBe('1 MB')
    })

    it('should format with custom decimals', () => {
      expect(formatBytes(1536, 0)).toBe('2 KB')
    })
  })

  describe('formatDuration', () => {
    it('should format seconds', () => {
      expect(formatDuration(30)).toBe('30.0s')
    })

    it('should format minutes', () => {
      expect(formatDuration(120)).toBe('2.0m')
    })

    it('should format hours', () => {
      expect(formatDuration(3600)).toBe('1.0h')
    })
  })

  describe('formatNumber', () => {
    it('should format small numbers', () => {
      expect(formatNumber(100)).toBe('100')
    })

    it('should format thousands', () => {
      expect(formatNumber(1500)).toBe('1.5K')
    })

    it('should format millions', () => {
      expect(formatNumber(1500000)).toBe('1.5M')
    })
  })
})
