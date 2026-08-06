'use client'

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Activity } from 'lucide-react'
import { useI18n } from '@/lib/i18n'
import { trend } from '@/lib/dashboard-data'

export function TrendChart() {
  const { t } = useI18n()

  return (
    <section className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-3 border-b border-border/70 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/25 bg-primary/12 text-primary">
            <Activity className="h-4.5 w-4.5" />
          </span>
          <div>
            <h3 className="text-sm font-semibold tracking-tight">{t('dash.trend.title')}</h3>
            <p className="text-xs text-muted-foreground">{t('dash.trend.subtitle')}</p>
          </div>
        </div>
        <div className="hidden items-center gap-4 sm:flex">
          <Legend color="var(--color-chart-1)" label={t('dash.trend.interactions')} />
          <Legend color="var(--color-chart-3)" label={t('dash.trend.compliance')} line />
        </div>
      </div>

      <div className="h-64 w-full p-4 pr-5">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trend} margin={{ top: 8, right: 4, bottom: 0, left: -16 }}>
            <defs>
              <linearGradient id="fillInteractions" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--color-border)" />
            <XAxis
              dataKey="day"
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--color-muted-foreground)', fontSize: 11 }}
              tickMargin={8}
            />
            <YAxis
              yAxisId="left"
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--color-muted-foreground)', fontSize: 11 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[80, 100]}
              hide
            />
            <Tooltip
              cursor={{ stroke: 'var(--color-border)' }}
              contentStyle={{
                background: 'var(--color-popover)',
                border: '1px solid var(--color-border)',
                borderRadius: 10,
                fontSize: 12,
                color: 'var(--color-foreground)',
              }}
              labelStyle={{ color: 'var(--color-muted-foreground)' }}
            />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="interactions"
              name={t('dash.trend.interactions')}
              stroke="var(--color-chart-1)"
              strokeWidth={2}
              fill="url(#fillInteractions)"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="compliance"
              name={t('dash.trend.compliance')}
              stroke="var(--color-chart-3)"
              strokeWidth={2}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function Legend({ color, label, line }: { color: string; label: string; line?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block rounded-full"
        style={{
          width: line ? 14 : 10,
          height: line ? 3 : 10,
          background: color,
        }}
      />
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}
