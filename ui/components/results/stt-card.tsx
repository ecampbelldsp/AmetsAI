'use client'

import { AudioLines } from 'lucide-react'
import { ResultCard, Metric } from '@/components/result-card'
import { useI18n } from '@/lib/i18n'
import type { Scenario } from '@/lib/scenarios'

function confColor(c: number) {
  if (c >= 0.95) return 'text-foreground'
  if (c >= 0.9) return 'text-foreground/85'
  if (c >= 0.85) return 'text-warning'
  return 'text-destructive'
}

export function SttCard({ scenario }: { scenario: Scenario }) {
  const { t, lang } = useI18n()
  const m = scenario.metrics
  const words = scenario.words[lang]

  return (
    <ResultCard icon={AudioLines} title={t('stt.title')} subtitle={t('stt.subtitle')} accent="accent">
      <p className="text-[15px] leading-relaxed tracking-tight text-pretty">
        {words.map((w, i) => (
          <span key={i} className={confColor(w.confidence)} title={`${(w.confidence * 100).toFixed(1)}%`}>
            {w.word}{' '}
          </span>
        ))}
      </p>

      <p className="mt-3 text-[11px] text-muted-foreground">{t('stt.legend')}</p>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Metric label={t('stt.duration')} value={`${m.audioDurationS.toFixed(1)} s`} />
        <Metric label={t('stt.inference')} value={`${m.inferenceMs} ms`} />
        <Metric label={t('stt.rtf')} value={m.rtf.toFixed(4)} />
        <Metric label={t('stt.latency')} value={`${m.endpointLatencyMs} ms`} />
        <Metric label={t('stt.confidence')} value={`${(m.avgConfidence * 100).toFixed(0)} %`} />
      </div>
    </ResultCard>
  )
}
