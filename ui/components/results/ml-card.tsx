'use client'

import { BrainCircuit, TrendingUp, ShieldHalf, Layers, Target } from 'lucide-react'
import { ResultCard } from '@/components/result-card'
import { useI18n } from '@/lib/i18n'
import type { MlInsights } from '@/lib/scenarios'
import { cn } from '@/lib/utils'

export function MlCard({ ml }: { ml: MlInsights }) {
  const { t, lang } = useI18n()
  const churnPct = Math.round(ml.churnRiskScore * 100)
  const churnLevel = churnPct < 25 ? 'low' : churnPct < 55 ? 'mid' : 'high'
  const churnColor =
    churnLevel === 'low' ? 'text-success' : churnLevel === 'mid' ? 'text-warning' : 'text-destructive'
  const churnBar =
    churnLevel === 'low' ? 'bg-success' : churnLevel === 'mid' ? 'bg-warning' : 'bg-destructive'

  return (
    <ResultCard
      icon={BrainCircuit}
      title={t('ml.title')}
      subtitle={t('ml.subtitle')}
      accent="primary"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-background p-3.5">
          <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
            <Layers className="h-3.5 w-3.5" /> {t('ml.segment')}
          </p>
          <p className="mt-1.5 text-sm font-semibold text-foreground">{ml.clientSegment}</p>
        </div>

        <div className="rounded-lg border border-border bg-background p-3.5">
          <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
            <Target className="h-3.5 w-3.5" /> {t('ml.tier')}
          </p>
          <p className="mt-1.5 text-sm font-semibold text-foreground">{ml.predictedValueTier}</p>
        </div>

        <div className="rounded-lg border border-border bg-background p-3.5">
          <div className="flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
              <ShieldHalf className="h-3.5 w-3.5" /> {t('ml.churn')}
            </p>
            <span className={cn('font-mono text-sm font-semibold', churnColor)}>{churnPct}%</span>
          </div>
          <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div className={cn('h-full rounded-full', churnBar)} style={{ width: `${churnPct}%` }} />
          </div>
          <p className={cn('mt-1.5 text-[11px] font-medium', churnColor)}>{t(`ml.churn.${churnLevel}`)}</p>
        </div>

        <div className="rounded-lg border border-primary/25 bg-primary/8 p-3.5">
          <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-primary/90">
            <TrendingUp className="h-3.5 w-3.5" /> {t('ml.action')}
          </p>
          <p className="mt-1.5 text-sm font-semibold text-foreground">
            {ml.recommendedActionType[lang]}
          </p>
        </div>
      </div>
    </ResultCard>
  )
}
