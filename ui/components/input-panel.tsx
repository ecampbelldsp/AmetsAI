'use client'

import { useEffect, useRef, useState } from 'react'
import { Mic, Upload, Sparkles, RotateCcw, Square, LoaderCircle, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/lib/i18n'
import { scenarios, type Scenario } from '@/lib/scenarios'
import { cn } from '@/lib/utils'

type Props = {
  value: string
  onChange: (v: string) => void
  activeScenario: Scenario['id'] | null
  onSelectScenario: (id: Scenario['id']) => void
  onAnalyze: () => void
  onReset: () => void
  isAnalyzing: boolean
  hasResult: boolean
  audioFile: File | null
  onFileChange: (file: File | null) => void
}

export function InputPanel({
  value,
  onChange,
  activeScenario,
  onSelectScenario,
  onAnalyze,
  onReset,
  isAnalyzing,
  hasResult,
  audioFile,
  onFileChange,
}: Props) {
  const { t, lang } = useI18n()
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [audioSrc, setAudioSrc] = useState<string | null>(null)

  useEffect(() => {
    if (audioFile) {
      const url = URL.createObjectURL(audioFile)
      setAudioSrc(url)

      return () => {
        URL.revokeObjectURL(url)
        setAudioSrc(null)
      }
    }
  }, [audioFile])

  useEffect(() => {
    if (recording) {
      timer.current = setInterval(() => setSeconds((s) => s + 1), 1000)
    } else if (timer.current) {
      clearInterval(timer.current)
    }
    return () => {
      if (timer.current) clearInterval(timer.current)
    }
  }, [recording])

  function stopRecording() {
    setRecording(false)
    setSeconds(0)
    // In a real scenario, this would trigger processing of the recorded audio
    // For now, we can simulate by selecting a default scenario or handling the blob
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null
    onFileChange(file)
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="audio/*"
        className="hidden"
      />
      <div>
        <h2 className="text-sm font-semibold tracking-tight">{t('input.title')}</h2>
        <p className="text-xs text-muted-foreground">{t('input.subtitle')}</p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {!recording ? (
          <button
            type="button"
            onClick={() => setRecording(true)}
            disabled={isAnalyzing}
            className="group flex items-center justify-center gap-2 rounded-lg border border-border bg-background px-3 py-2.5 text-sm font-medium transition-colors hover:border-primary/50 hover:bg-primary/5 disabled:opacity-50"
          >
            <Mic className="h-4 w-4 text-primary" />
            {t('input.record')}
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            className="flex items-center justify-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2.5 text-sm font-medium text-destructive"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            {t('input.recording')} {String(Math.floor(seconds / 60)).padStart(2, '0')}:
            {String(seconds % 60).padStart(2, '0')}
          </button>
        )}

        <button
          type="button"
          onClick={handleUploadClick}
          disabled={isAnalyzing || recording}
          className="flex items-center justify-center gap-2 rounded-lg border border-border bg-background px-3 py-2.5 text-sm font-medium transition-colors hover:border-accent/50 hover:bg-accent/5 disabled:opacity-50"
        >
          <Upload className="h-4 w-4 text-accent" />
          {t('input.upload')}
        </button>
      </div>

      {audioFile && audioSrc && (
        <div className="flex flex-col gap-2 rounded-lg bg-background p-2.5 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Paperclip className="h-4 w-4 shrink-0" />
            <span className="truncate" title={audioFile.name}>
              {audioFile.name}
            </span>
          </div>
          <audio src={audioSrc} controls className="h-10 w-full" />
        </div>
      )}

      {recording && (
        <div className="flex h-10 items-end gap-1 overflow-hidden rounded-lg bg-background px-3 py-2">
          {Array.from({ length: 40 }).map((_, i) => (
            <span
              key={i}
              className="w-1 shrink-0 rounded-full bg-primary/70"
              style={{
                height: `${20 + Math.abs(Math.sin(i * 0.9 + seconds)) * 70}%`,
                transition: 'height 0.25s ease',
              }}
            />
          ))}
        </div>
      )}

      <div>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={isAnalyzing || !!audioFile}
          rows={5}
          placeholder={t('input.placeholder')}
          className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/60 focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
        />
      </div>

      <div>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {t('input.scenario')}
        </p>
        <div className="grid grid-cols-2 gap-2">
          {(['compliant', 'alert'] as const).map((id) => {
            const active = activeScenario === id
            return (
              <button
                key={id}
                type="button"
                onClick={() => onSelectScenario(id)}
                disabled={isAnalyzing || recording || !!audioFile}
                className={cn(
                  'rounded-lg border px-3 py-2 text-left text-xs font-medium transition-colors disabled:opacity-50',
                  active
                    ? id === 'alert'
                      ? 'border-destructive/50 bg-destructive/10 text-destructive'
                      : 'border-success/50 bg-success/10 text-success'
                    : 'border-border bg-background text-foreground hover:border-primary/40',
                )}
              >
                <span className="block">{t(`input.scenario.${id}`)}</span>
                <span className="mt-0.5 block text-[10px] font-normal opacity-70">
                  {scenarios[id].client} · {scenarios[id].specialty[lang]}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={onAnalyze}
          disabled={isAnalyzing || (!value.trim() && !audioFile)}
          className="flex-1 gap-2"
        >
          {isAnalyzing ? (
            <>
              <LoaderCircle className="h-4 w-4 animate-spin" />
              {t('input.analyzing')}
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              {t('input.analyze')}
            </>
          )}
        </Button>
        {(hasResult || value || audioFile) && !isAnalyzing && (
          <Button variant="outline" onClick={onReset} className="gap-2 bg-transparent">
            <RotateCcw className="h-4 w-4" />
            <span className="hidden sm:inline">{t('input.reset')}</span>
          </Button>
        )}
      </div>
    </div>
  )
}
