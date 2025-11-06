import * as React from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

const Dialog = ({ open, onOpenChange, children }: DialogProps) => {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => onOpenChange?.(false)}
          />
          {/* Content */}
          <div className="relative z-50">{children}</div>
        </div>
      )}
    </>
  )
}

const DialogContent = React.forwardRef<HTMLDivElement, DialogContentProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'relative bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
DialogContent.displayName = 'DialogContent'

interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

const DialogHeader = ({ className, children, ...props }: DialogHeaderProps) => {
  return (
    <div className={cn('mb-4', className)} {...props}>
      {children}
    </div>
  )
}

interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

const DialogTitle = ({ className, children, ...props }: DialogTitleProps) => {
  return (
    <h2
      className={cn('text-xl font-semibold', className)}
      {...props}
    >
      {children}
    </h2>
  )
}

interface DialogDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

const DialogDescription = ({ className, children, ...props }: DialogDescriptionProps) => {
  return (
    <p
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    >
      {children}
    </p>
  )
}

interface DialogCloseProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  onClose: () => void
}

const DialogClose = ({ onClose, className, ...props }: DialogCloseProps) => {
  return (
    <button
      onClick={onClose}
      className={cn(
        'absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100',
        className
      )}
      {...props}
    >
      <X className="h-4 w-4" />
      <span className="sr-only">Close</span>
    </button>
  )
}

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogClose }
