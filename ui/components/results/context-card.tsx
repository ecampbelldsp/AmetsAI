'use client'

import { Database, Briefcase, Stethoscope } from 'lucide-react'
import { ResultCard } from '@/components/result-card'
import { useI18n } from '@/lib/i18n'
import type { Scenario } from '@/lib/scenarios'

export function ContextCard({ scenario }: { scenario: Scenario }) {
  const { t, lang } = useI18n()

  const corpora = [
    {
      icon: Briefcase,
      label: t('rag.commercial'),
      doc: scenario.commercialContext,
      tint: 'text-primary',
    },
    {
      icon: Stethoscope,
      label: t('rag.clinical'),
      doc: scenario.clinicalContext,
      tint: 'text-accent',
    },
  ]

  return (
    <ResultCard icon={Database} title={t('rag.title')} subtitle={t('rag.subtitle')} accent="primary">
      <div className="grid gap-3 md:grid-cols-2">
        {corpora.map(({ icon: Icon, label, doc, tint }) => (
          <div key={doc.id} className="rounded-lg border border-border bg-background p-3.5">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className={`flex items-center gap-1.5 text-xs font-medium ${tint}`}>
                <Icon className="h-3.5 w-3.5" />
                {label}
              </span>
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                {doc.id}
              </code>
            </div>
            <p className="text-xs font-medium text-foreground">{doc.title[lang]}</p>
            <pre className="mt-1.5 whitespace-pre-wrap font-sans text-xs leading-relaxed text-muted-foreground">
              {doc.body[lang]}
            </pre>
          </div>
        ))}
      </div>
    </ResultCard>
  )
}
