'use client'

import { ShieldAlert } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import { alerts } from '@/lib/dashboard-data'
import { cn } from '@/lib/utils'

const statusStyles: Record<string, string> = {
  open: 'bg-destructive/12 text-destructive border-destructive/25',
  review: 'bg-warning/12 text-warning border-warning/25',
  resolved: 'bg-success/12 text-success border-success/25',
}

export function AlertsPanel() {
  const { t, lang } = useI18n()

  return (
    <section className="flex flex-col rounded-xl border border-border bg-card">
      <div className="flex items-center gap-3 border-b border-border/70 px-5 py-4">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-destructive/25 bg-destructive/12 text-destructive">
          <ShieldAlert className="h-4.5 w-4.5" />
        </span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold tracking-tight">{t('dash.alerts.title')}</h3>
          <p className="text-xs text-muted-foreground">{t('dash.alerts.subtitle')}</p>
        </div>
        <span className="rounded-full border border-destructive/25 bg-destructive/12 px-2 py-0.5 font-mono text-xs font-semibold text-destructive">
          {alerts.filter((a) => a.status === 'open').length}
        </span>
      </div>

      <ul className="divide-y divide-border/60">
        {alerts.map((a) => (
          <li key={a.id} className="flex flex-col gap-2 px-5 py-3.5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-muted-foreground">{a.id}</span>
                <span className="text-sm font-medium">{a.client}</span>
              </div>
              <span
                className={cn(
                  'rounded-md border px-2 py-0.5 text-[11px] font-medium',
                  statusStyles[a.status],
                )}
              >
                {t(`dash.alerts.${a.status === 'open' ? 'open' : a.status === 'review' ? 'review' : 'resolved'}`)}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground text-pretty">
              {a.reason[lang]}
            </p>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span>
                {t('dash.alerts.rep')}: <span className="text-foreground">{a.rep}</span>
              </span>
              <span aria-hidden>·</span>
              <span>{a.time[lang]}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
