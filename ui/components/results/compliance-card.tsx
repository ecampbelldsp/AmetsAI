'use client'

import { ShieldCheck, ShieldAlert } from 'lucide-react'
import { ResultCard } from '@/components/result-card'
import { useI18n } from '@/lib/i18n'
import type { Scenario } from '@/lib/scenarios'
import { cn } from '@/lib/utils'

export function ComplianceCard({ scenario }: { scenario: Scenario }) {
  const { t, lang } = useI18n()
  const ok = scenario.isCompliant

  return (
    <ResultCard
      icon={ok ? ShieldCheck : ShieldAlert}
      title={t('compliance.title')}
      subtitle={t('compliance.subtitle')}
      accent={ok ? 'success' : 'destructive'}
      badge={
        <span
          className={cn(
            'shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold',
            ok
              ? 'border-success/40 bg-success/12 text-success'
              : 'border-destructive/40 bg-destructive/12 text-destructive',
          )}
        >
          {ok ? t('compliance.pass') : t('compliance.fail')}
        </span>
      }
    >
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {t('compliance.cot')}
      </p>
      <ol className="flex flex-col gap-2">
        {scenario.complianceChainOfThought[lang].map((step, i) => (
          <li key={i} className="flex gap-2.5 rounded-lg border border-border bg-background p-3">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-muted font-mono text-[11px] text-muted-foreground">
              {i + 1}
            </span>
            <span className="text-xs leading-relaxed text-foreground">{step}</span>
          </li>
        ))}
      </ol>

      <div
        className={cn(
          'mt-3 rounded-lg border p-3',
          ok ? 'border-success/25 bg-success/8' : 'border-destructive/25 bg-destructive/8',
        )}
      >
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {t('compliance.reasoning')}
        </p>
        <p className="mt-1 text-xs leading-relaxed text-foreground">
          {scenario.complianceReasoning[lang]}
        </p>
      </div>
    </ResultCard>
  )
}
