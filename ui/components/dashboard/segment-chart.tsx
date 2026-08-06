'use client'

import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts'
import { PieChart as PieIcon } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import { segments } from '@/lib/dashboard-data'

export function SegmentChart() {
  const { t, lang } = useI18n()
  const data = segments.map((s) => ({ ...s, name: s.label[lang] }))

  return (
    <section className="rounded-xl border border-border bg-card">
      <div className="flex items-center gap-3 border-b border-border/70 px-5 py-4">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-accent/25 bg-accent/12 text-accent">
          <PieIcon className="h-4.5 w-4.5" />
        </span>
        <div>
          <h3 className="text-sm font-semibold tracking-tight">{t('dash.segments.title')}</h3>
          <p className="text-xs text-muted-foreground">{t('dash.segments.subtitle')}</p>
        </div>
      </div>

      <div className="flex flex-col items-center gap-5 p-5 sm:flex-row">
        <div className="relative h-40 w-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                innerRadius={52}
                outerRadius={78}
                paddingAngle={2}
                stroke="var(--color-card)"
                strokeWidth={2}
              >
                {data.map((entry) => (
                  <Cell key={entry.key} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-2xl font-semibold">342</span>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {lang === 'es' ? 'Prescriptores' : 'Prescribers'}
            </span>
          </div>
        </div>

        <ul className="flex w-full flex-1 flex-col gap-2.5">
          {data.map((s) => (
            <li key={s.key} className="flex items-center gap-2.5">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ background: s.color }}
              />
              <span className="flex-1 text-sm text-foreground">{s.name}</span>
              <span className="font-mono text-sm font-semibold text-muted-foreground">
                {s.value}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
