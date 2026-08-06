'use client'

import { AudioLines, BrainCircuit, Database, ShieldCheck, Target, Check, LoaderCircle } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export type StageState = 'idle' | 'running' | 'done' | 'blocked'

export type Stage = {
  key: 'stt' | 'rag' | 'compliance' | 'ml' | 'insight'
  state: StageState
}

const icons = {
  stt: AudioLines,
  rag: Database,
  compliance: ShieldCheck,
  ml: BrainCircuit,
  insight: Target,
}

export function PipelineRail({ stages }: { stages: Stage[] }) {
  const { t } = useI18n()

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="mb-4 px-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {t('pipeline.title')}
      </p>
      <ol className="flex flex-col gap-1">
        {stages.map((stage, i) => {
          const Icon = icons[stage.key]
          const isLast = i === stages.length - 1
          return (
            <li key={stage.key} className="relative flex items-start gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors',
                    stage.state === 'idle' && 'border-border bg-background text-muted-foreground',
                    stage.state === 'running' && 'border-primary/50 bg-primary/15 text-primary',
                    stage.state === 'done' && 'border-success/40 bg-success/15 text-success',
                    stage.state === 'blocked' && 'border-destructive/40 bg-destructive/15 text-destructive',
                  )}
                >
                  {stage.state === 'running' ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : stage.state === 'done' ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </span>
                {!isLast && (
                  <span
                    className={cn(
                      'my-0.5 w-px flex-1 grow bg-border',
                      stage.state === 'done' && 'bg-success/40',
                    )}
                    style={{ minHeight: 18 }}
                  />
                )}
              </div>
              <div className="pb-3 pt-1">
                <p
                  className={cn(
                    'text-sm font-medium leading-none transition-colors',
                    stage.state === 'idle' ? 'text-muted-foreground' : 'text-foreground',
                  )}
                >
                  {t(`pipeline.${stage.key}`)}
                </p>
                <p
                  className={cn(
                    'mt-1 text-[11px]',
                    stage.state === 'running' && 'text-primary',
                    stage.state === 'done' && 'text-success',
                    stage.state === 'blocked' && 'text-destructive',
                    stage.state === 'idle' && 'text-muted-foreground/60',
                  )}
                >
                  {t(`pipeline.${stage.state === 'idle' ? 'waiting' : stage.state}`)}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
