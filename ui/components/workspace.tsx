'use client'

import { useCallback, useRef, useState } from 'react'
import { Waypoints, Radar } from 'lucide-react'
import { InputPanel } from '@/components/input-panel'
import { PipelineRail, type Stage, type StageState } from '@/components/pipeline-rail'
import { SttCard } from '@/components/results/stt-card'
import { ContextCard } from '@/components/results/context-card'
import { ComplianceCard } from '@/components/results/compliance-card'
import { MlCard } from '@/components/results/ml-card'
import { InsightCard } from '@/components/results/insight-card'
import { AlertCard } from '@/components/results/alert-card'
import { useI18n } from '@/lib/i18n'
import { scenarios, type Scenario } from '@/lib/scenarios'

const STAGE_KEYS = ['stt', 'rag', 'compliance', 'ml', 'insight'] as const
type StageKey = (typeof STAGE_KEYS)[number]

const idleStages: Stage[] = STAGE_KEYS.map((key) => ({ key, state: 'idle' }))

export function Workspace() {
  const { t, lang } = useI18n()
  const [text, setText] = useState('')
  const [activeId, setActiveId] = useState<Scenario['id'] | null>(null)
  const [stages, setStages] = useState<Stage[]>(idleStages)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<Scenario | null>(null)
  const [visible, setVisible] = useState<Set<StageKey>>(new Set())
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  const clearTimers = () => {
    timers.current.forEach(clearTimeout)
    timers.current = []
  }

  const selectScenario = useCallback(
    (id: Scenario['id']) => {
      clearTimers()
      setActiveId(id)
      setText(scenarios[id].transcription[lang])
      setResult(null)
      setStages(idleStages)
      setVisible(new Set())
    },
    [lang],
  )

  const reset = useCallback(() => {
    clearTimers()
    setText('')
    setActiveId(null)
    setResult(null)
    setStages(idleStages)
    setVisible(new Set())
    setIsAnalyzing(false)
  }, [])

  const setStage = (key: StageKey, state: StageState) =>
    setStages((prev) => prev.map((s) => (s.key === key ? { ...s, state } : s)))

  const analyze = useCallback(() => {
    const scenario = activeId ? scenarios[activeId] : scenarios.compliant
    clearTimers()
    setIsAnalyzing(true)
    setResult(scenario)
    setVisible(new Set())
    setStages(idleStages)

    const push = (fn: () => void, delay: number) => timers.current.push(setTimeout(fn, delay))
    const reveal = (key: StageKey) => setVisible((prev) => new Set(prev).add(key))

    // STT
    push(() => setStage('stt', 'running'), 200)
    push(() => {
      setStage('stt', 'done')
      reveal('stt')
    }, 1100)

    // RAG
    push(() => setStage('rag', 'running'), 1150)
    push(() => {
      setStage('rag', 'done')
      reveal('rag')
    }, 1900)

    // Compliance
    push(() => setStage('compliance', 'running'), 1950)
    push(() => {
      setStage('compliance', scenario.isCompliant ? 'done' : 'blocked')
      reveal('compliance')
    }, 2900)

    if (scenario.isCompliant) {
      // ML scoring
      push(() => setStage('ml', 'running'), 2950)
      push(() => {
        setStage('ml', 'done')
        reveal('ml')
      }, 3800)
      // Insight
      push(() => setStage('insight', 'running'), 3850)
      push(() => {
        setStage('insight', 'done')
        reveal('insight')
        setIsAnalyzing(false)
      }, 4800)
    } else {
      // Downstream stages blocked
      push(() => {
        setStages((prev) =>
          prev.map((s) => (s.key === 'ml' || s.key === 'insight' ? { ...s, state: 'blocked' } : s)),
        )
        reveal('insight') // used to reveal the alert block
        setIsAnalyzing(false)
      }, 3100)
    }
  }, [activeId])

  const hasResult = result !== null
  const show = (k: StageKey) => visible.has(k)

  return (
    <div className="min-h-svh">
      <main className="mx-auto max-w-7xl px-5 pb-20 pt-8 md:px-8">
        {/* Hero */}
        <div className="mb-8 max-w-3xl">
          <span className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
            <Radar className="h-3.5 w-3.5 text-accent" />
            {t('nav.workspace')}
          </span>
          <h1 className="text-3xl font-semibold tracking-tight text-balance md:text-4xl">
            {t('hero.title')}
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground md:text-base text-pretty">
            {t('hero.subtitle')}
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(320px,380px)_1fr]">
          {/* Left column: input + pipeline */}
          <div className="flex flex-col gap-4 lg:sticky lg:top-24 lg:self-start">
            <InputPanel
              value={text}
              onChange={setText}
              activeScenario={activeId}
              onSelectScenario={selectScenario}
              onAnalyze={analyze}
              onReset={reset}
              isAnalyzing={isAnalyzing}
              hasResult={hasResult}
            />
            <PipelineRail stages={stages} />
          </div>

          {/* Right column: results */}
          <div className="flex flex-col gap-4">
            {!hasResult ? (
              <div className="grid-bg flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 p-10 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-card">
                  <Waypoints className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="mt-4 text-sm font-medium">{t('empty.title')}</p>
                <p className="mt-1 max-w-sm text-sm text-muted-foreground text-pretty">
                  {t('empty.body')}
                </p>
              </div>
            ) : (
              <>
                {show('stt') && result && <SttCard scenario={result} />}
                {show('rag') && result && <ContextCard scenario={result} />}
                {show('compliance') && result && <ComplianceCard scenario={result} />}
                {result?.isCompliant && show('ml') && result.ml && <MlCard ml={result.ml} />}
                {result?.isCompliant && show('insight') && <InsightCard scenario={result} />}
                {result && !result.isCompliant && show('insight') && <AlertCard scenario={result} />}
              </>
            )}
          </div>
        </div>

        <footer className="mt-14 border-t border-border pt-6">
          <p className="text-center text-xs text-muted-foreground">{t('footer.note')}</p>
        </footer>
      </main>
    </div>
  )
}
