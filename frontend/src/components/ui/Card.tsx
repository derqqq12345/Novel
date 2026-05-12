import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
  hover?: boolean
}

export default function Card({
  children,
  className = '',
  onClick,
  hover = false,
}: CardProps) {
  const hoverStyles = hover
    ? 'hover:shadow-lg hover:scale-[1.02] transition-all cursor-pointer'
    : ''

  return (
    <div
      className={`bg-white dark:bg-gray-900 rounded-lg shadow-md border border-gray-200 dark:border-gray-800 ${hoverStyles} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`px-6 py-4 border-b border-gray-200 dark:border-gray-800 ${className}`}
    >
      {children}
    </div>
  )
}

export function CardBody({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={`px-6 py-4 ${className}`}>{children}</div>
}

export function CardFooter({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`px-6 py-4 border-t border-gray-200 dark:border-gray-800 ${className}`}
    >
      {children}
    </div>
  )
}
