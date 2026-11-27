import type { ReactNode } from 'react'

interface BadgeProps {
  /** Color variant: a priority, a status or a neutral tone (see index.css `.badge-*`). */
  tone: string
  children: ReactNode
}

export default function Badge({ tone, children }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}
