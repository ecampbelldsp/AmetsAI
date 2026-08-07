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
import { type Scenario, type Doc } from '@/lib/scenarios'

const STAGE_KEYS = ['stt', 'rag', 'compliance', 'ml', 'insight'] as const
type StageKey = (typeof STAGE_KEYS)[number]

const idleStages: Stage[] = STAGE_KEYS.map((key) => ({ key, state: 'idle' }))

// Define a type for the API response
type AnalysisResult = {
  transcription: string
  is_compliant: boolean | string
  compliance_reasoning: string
  compliance_chain_of_thought: string[]
  strategic_insight: string
  final_recommendation: string
  commercial_context: Doc
  clinical_context: Doc
  ml_insights: {
    client_segment: string
    churn_risk_score: number
    predicted_value_tier: string
    recommended_action_type: string
  }
}

export function Workspace() {
  const { t, lang } = useI18n()
  const [text, setText] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [activeId, setActiveId] = useState<Scenario['id'] | null>(null)
  const [stages, setStages] = useState<Stage[]>(idleStages)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
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
      // This is a mock implementation, replace with actual logic if needed
      const mockScenarios = {
        compliant: { transcription: { [lang]: 'Compliant transcription example.' } },
        alert: { transcription: { [lang]: 'Alert transcription example.' } },
      }
      setText(mockScenarios[id].transcription[lang])
      setResult(null)
      setStages(idleStages)
      setVisible(new Set())
      setAudioFile(null)
    },
    [lang],
  )

  const reset = useCallback(() => {
    clearTimers()
    setText('')
    setAudioFile(null)
    setActiveId(null)
    setResult(null)
    setStages(idleStages)
    setVisible(new Set())
    setIsAnalyzing(false)
  }, [])

  const setStage = (key: StageKey, state: StageState) =>
    setStages((prev) => prev.map((s) => (s.key === key ? { ...s, state } : s)))

  const analyze = useCallback(async () => {
    if (!audioFile && !text.trim()) return

    clearTimers()
    setIsAnalyzing(true)
    setResult(null)
    setVisible(new Set())
    setStages(idleStages)

    const reveal = (key: StageKey) => setVisible((prev) => new Set(prev).add(key))

    try {
      let analysisResult: AnalysisResult

      if (audioFile) {
        const formData = new FormData()
        formData.append('file', audioFile)

        setStage('stt', 'running')
        const response = await fetch('http://127.0.0.1:8000/process-audio/', {
          method: 'POST',
          body: formData,
        })
        setStage('stt', 'done')
        reveal('stt')

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        analysisResult = await response.json()
        setText(analysisResult.transcription)
      } else {
        // ✅ ELIMINADO EL MOCK: Ahora enviamos el texto directamente a LangGraph
        setStage('stt', 'running')

        const response = await fetch('http://127.0.0.1:8000/process-text/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: text }),
        })

        setStage('stt', 'done')
        reveal('stt')

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        analysisResult = await response.json()
      }

      setResult(analysisResult)

      // Animate the rest of the pipeline based on the result
      const push = (fn: () => void, delay: number) => timers.current.push(setTimeout(fn, delay))

      push(() => setStage('rag', 'running'), 50)
      push(() => {
        setStage('rag', 'done')
        reveal('rag')
      }, 750)

      push(() => setStage('compliance', 'running'), 800)
      push(() => {
        const isCompliant =
          analysisResult.is_compliant === true || analysisResult.is_compliant === 'true'
        setStage('compliance', isCompliant ? 'done' : 'blocked')
        reveal('compliance')

        if (isCompliant) {
          push(() => setStage('ml', 'running'), 50)
          push(() => {
            setStage('ml', 'done')
            reveal('ml')
          }, 850)
          push(() => setStage('insight', 'running'), 900)
          push(() => {
            setStage('insight', 'done')
            reveal('insight')
            setIsAnalyzing(false)
          }, 1800)
        } else {
          push(() => {
            setStages((prev) =>
              prev.map((s) =>
                s.key === 'ml' || s.key === 'insight' ? { ...s, state: 'blocked' } : s,
              ),
            )
            reveal('insight') // Reveals the alert block
            setIsAnalyzing(false)
          }, 200)
        }
      }, 1000)
    } catch (error) {
      console.error('Analysis failed:', error)
      // Handle error state in UI
      setStages(idleStages.map((s) => ({ ...s, state: 'blocked' })))
      setIsAnalyzing(false)
    }
  }, [audioFile, text, activeId])

  const hasResult = result !== null
  const show = (k: StageKey) => visible.has(k)
  const isCompliant = result?.is_compliant === true || result?.is_compliant === 'true'

  const resultAsScenario: Scenario | null = result
    ? {
        id: 'compliant',
        isCompliant,
        transcription: { en: result.transcription, es: result.transcription },
        complianceReasoning: { en: result.compliance_reasoning, es: result.compliance_reasoning },
        complianceChainOfThought: { en: result.compliance_chain_of_thought, es: result.compliance_chain_of_thought },
        strategicInsight: { en: result.strategic_insight, es: result.strategic_insight },
        tacticalActions: {
          en: result.final_recommendation.split('\n').map(r => r.replace(/^-\s*/, '').trim()).filter(Boolean),
          es: result.final_recommendation.split('\n').map(r => r.replace(/^-\s*/, '').trim()).filter(Boolean),
        },
        client: result.commercial_context?.title?.es?.replace('Visita a ', '') || 'Dr. Garcia',
        specialty: { en: 'Endocrinology', es: 'Endocrinología' },
        ml: {
          score: Math.round((1 - (result.ml_insights?.churn_risk_score || 0)) * 100),
          churnRiskScore: result.ml_insights?.churn_risk_score || 0.12,
          profile: result.ml_insights?.client_segment || 'N/A',
          clientSegment: result.ml_insights?.client_segment || 'N/A',
          segment: result.ml_insights?.client_segment || 'N/A',
          valueTier: result.ml_insights?.predicted_value_tier || 'N/A',
          predictedValueTier: result.ml_insights?.predicted_value_tier || 'N/A',
          tier: result.ml_insights?.predicted_value_tier || 'N/A',
          recommendedActionType: {
            es: result.ml_insights?.recommended_action_type || 'N/A',
            en: result.ml_insights?.recommended_action_type || 'N/A'
          },
          actionType: {
            es: result.ml_insights?.recommended_action_type || 'N/A',
            en: result.ml_insights?.recommended_action_type || 'N/A'
          }
        },
        metrics: {
          audioDurationS: 0,
          inferenceMs: 0,
          rtf: 0,
          endpointLatencyMs: 0,
          words: 0,
          wpm: 0,
          talkToListen: [0, 0],
        },
        words: { es: [], en: [] },
        commercialContext: result.commercial_context,
        clinicalContext: result.clinical_context,
      }
    : null

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
              audioFile={audioFile}
              onFileChange={setAudioFile}
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
              resultAsScenario && (
                <>
                  {show('stt') && <SttCard scenario={resultAsScenario} />}
                  {show('rag') && <ContextCard scenario={resultAsScenario} />}
                  {show('compliance') && <ComplianceCard scenario={resultAsScenario} />}
                  {isCompliant && show('ml') && resultAsScenario.ml && (
                    <MlCard ml={resultAsScenario.ml} />
                  )}
                  {isCompliant && show('insight') && <InsightCard scenario={resultAsScenario} />}
                  {!isCompliant && show('insight') && <AlertCard scenario={resultAsScenario} />}
                </>
              )
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
