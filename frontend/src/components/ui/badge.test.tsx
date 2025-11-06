import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from './badge'

describe('Badge', () => {
  it('should render badge with text', () => {
    render(<Badge>Test Badge</Badge>)
    expect(screen.getByText('Test Badge')).toBeInTheDocument()
  })

  it('should apply default variant', () => {
    const { container } = render(<Badge>Default</Badge>)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-primary')
  })

  it('should apply success variant', () => {
    const { container } = render(<Badge variant="success">Success</Badge>)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-green-600')
  })

  it('should apply destructive variant', () => {
    const { container } = render(<Badge variant="destructive">Error</Badge>)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-destructive')
  })

  it('should apply warning variant', () => {
    const { container } = render(<Badge variant="warning">Warning</Badge>)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('bg-yellow-500')
  })

  it('should apply custom className', () => {
    const { container } = render(<Badge className="custom-class">Custom</Badge>)
    const badge = container.querySelector('.inline-flex')
    expect(badge).toHaveClass('custom-class')
  })
})
