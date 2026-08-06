'use client'

import { TrendingUp, TrendingDown } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import { kpis } from '@/lib/dashboard-data'
import { cn } from '@/lib/utils'

export function KpiCards() {
  const { t } = useI18n()

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {kpis.map((kpi) => {
        const isGood = kpi.delta >= 0 === kpi.positiveIsGood
        const Icon = kpi.delta >= 0 ? TrendingUp : TrendingDown
        return (
          <div
            key={kpi.key}
            className="rounded-xl border border-border bg-card p-4 md:p-5"
          >
            <p className="text-xs text-muted-foreground text-pretty">{t(kpi.key)}</p>
            <p className="mt-2 font-mono text-2xl font-semibold tracking-tight md:text-3xl">
              {kpi.value}
            </p>
            <div className="mt-3 flex items-center gap-1.5">
              <span
                className={cn(
                  'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium',
                  isGood
                    ? 'bg-success/12 text-success'
                    : 'bg-destructive/12 text-destructive',
                )}
              >
                <Icon className="h-3 w-3" />
                {kpi.delta > 0 ? '+' : ''}
                {kpi.delta.toLocaleString('es-ES', { minimumFractionDigits: 1 })}%
              </span>
              <span className="text-[11px] text-muted-foreground">{t('dash.kpi.vsPrev')}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
