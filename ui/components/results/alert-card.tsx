'use client'

import { TriangleAlert, BellRing, Ban } from 'lucide-react'
import { ResultCard } from '@/components/result-card'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/lib/i18n'
import type { Scenario } from '@/lib/scenarios'

export function AlertCard({ scenario }: { scenario: Scenario }) {
  const { t, lang } = useI18n()

  return (
    <ResultCard
      icon={TriangleAlert}
      title={t('alert.title')}
      subtitle={scenario.client}
      accent="destructive"
      badge={
        <span className="flex shrink-0 items-center gap-1 rounded-full border border-destructive/40 bg-destructive/12 px-2.5 py-1 text-[11px] font-semibold text-destructive">
          <Ban className="h-3 w-3" /> CRM
        </span>
      }
    >
      <div className="rounded-lg border border-destructive/25 bg-destructive/8 p-4">
        <p className="text-sm leading-relaxed text-foreground text-pretty">{t('alert.body')}</p>
        <p className="mt-3 border-t border-destructive/20 pt-3 text-xs leading-relaxed text-muted-foreground">
          {scenario.complianceReasoning[lang]}
        </p>
      </div>

      <Button variant="outline" className="mt-4 w-full gap-2 border-destructive/40 bg-transparent text-destructive hover:bg-destructive/10 hover:text-destructive">
        <BellRing className="h-4 w-4" />
        {t('alert.notify')}
      </Button>
    </ResultCard>
  )
}
