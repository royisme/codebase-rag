import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Input } from './input'
import userEvent from '@testing-library/user-event'

describe('Input', () => {
  it('should render input field', () => {
    render(<Input placeholder="Enter text" />)
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
  })

  it('should handle text input', async () => {
    const user = userEvent.setup()
    render(<Input />)
    const input = screen.getByRole('textbox')

    await user.type(input, 'Hello')
    expect(input).toHaveValue('Hello')
  })

  it('should be disabled when disabled prop is true', () => {
    render(<Input disabled />)
    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('should accept different input types', () => {
    const { container } = render(<Input type="email" />)
    const input = container.querySelector('input')
    expect(input).toHaveAttribute('type', 'email')
  })

  it('should apply custom className', () => {
    const { container } = render(<Input className="custom-input" />)
    const input = container.querySelector('input')
    expect(input).toHaveClass('custom-input')
  })
})
