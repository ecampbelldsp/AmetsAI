'use client'

import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Accent = 'primary' | 'accent' | 'success' | 'destructive' | 'warning'

const accentMap: Record<Accent, string> = {
  primary: 'text-primary bg-primary/12 border-primary/25',
  accent: 'text-accent bg-accent/12 border-accent/25',
  success: 'text-success bg-success/12 border-success/25',
  destructive: 'text-destructive bg-destructive/12 border-destructive/25',
  warning: 'text-warning bg-warning/12 border-warning/25',
}

export function ResultCard({
  icon: Icon,
  title,
  subtitle,
  accent = 'primary',
  badge,
  children,
}: {
  icon: LucideIcon
  title: string
  subtitle?: string
  accent?: Accent
  badge?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="animate-in fade-in slide-in-from-bottom-2 overflow-hidden rounded-xl border border-border bg-card duration-500">
      <div className="flex items-center gap-3 border-b border-border/70 px-5 py-4">
        <span
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border',
            accentMap[accent],
          )}
        >
          <Icon className="h-4.5 w-4.5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold tracking-tight">{title}</h3>
          {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {badge}
      </div>
      <div className="p-5">{children}</div>
    </section>
  )
}

export function Metric({
  label,
  value,
  mono = true,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="rounded-lg border border-border bg-background px-3 py-2.5">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={cn('mt-1 text-sm font-semibold text-foreground', mono && 'font-mono')}>
        {value}
      </p>
    </div>
  )
}
