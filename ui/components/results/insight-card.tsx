'use client'

import { Target, BrainCircuit, TrendingUp, ArrowRight, Send } from 'lucide-react'
import type { ReactNode } from 'react'
import { ResultCard } from '@/components/result-card'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/lib/i18n'
import type { Scenario } from '@/lib/scenarios'

// Renders [Source: ID] citations as inline badges.
function withCitations(text: string, sourceLabel: string): ReactNode {
  const parts = text.split(/(\[Source:[^\]]+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[Source:\s*([^\]]+)\]/)
    if (match) {
      return (
        <span
          key={i}
          className="mx-0.5 inline-flex items-center gap-1 rounded-md border border-accent/40 bg-accent/12 px-1.5 py-0.5 align-middle font-mono text-[10px] font-medium text-accent"
        >
          {sourceLabel}: {match[1].trim()}
        </span>
      )
    }
    return <span key={i}>{part}</span>
  })
}

export function InsightCard({ scenario }: { scenario: Scenario }) {
  const { t, lang } = useI18n()
  if (!scenario.ml || !scenario.strategicInsight || !scenario.tacticalActions) return null

  return (
    <ResultCard
      icon={Target}
      title={t('insight.title')}
      subtitle={t('insight.subtitle')}
      accent="success"
    >
      <div className="rounded-lg border border-primary/25 bg-primary/8 p-4">
        <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-primary/90">
          <BrainCircuit className="h-3.5 w-3.5" /> {t('insight.ml')}
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-foreground text-pretty">
          {scenario.mlRationale?.[lang]}
        </p>
      </div>

      <div className="mt-3 rounded-lg border border-border bg-background p-4">
        <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          <TrendingUp className="h-3.5 w-3.5" /> {t('insight.strategy')}
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-foreground text-pretty">
          {scenario.strategicInsight[lang]}
        </p>
      </div>

      <p className="mb-2 mt-4 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {t('insight.tactics')}
      </p>
      <ul className="flex flex-col gap-2">
        {scenario.tacticalActions[lang].map((action, i) => (
          <li
            key={i}
            className="flex items-start gap-2.5 rounded-lg border border-success/25 bg-success/8 p-3"
          >
            <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-success" />
            <span className="text-sm leading-relaxed text-foreground">
              {withCitations(action, t('insight.source'))}
            </span>
          </li>
        ))}
      </ul>

      <Button className="mt-4 w-full gap-2">
        <Send className="h-4 w-4" />
        {t('insight.deliver')}
      </Button>
    </ResultCard>
  )
}
