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
    const handleClick = () => {
      clicked = true
    }

    render(<Button onClick={handleClick}>Click me</Button>)
    await user.click(screen.getByRole('button'))

    expect(clicked).toBe(true)
  })

  it('should be disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('should apply variant classes', () => {
    const { container } = render(<Button variant="destructive">Delete</Button>)
    const button = container.querySelector('button')
    expect(button).toHaveClass('bg-destructive')
  })

  it('should apply size classes', () => {
    const { container } = render(<Button size="sm">Small</Button>)
    const button = container.querySelector('button')
    expect(button).toHaveClass('h-9')
  })
})
