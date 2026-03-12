import dayjs from 'dayjs'
import * as yaml from 'js-yaml'
import {
  getTargetMetricLatest,
  getTargetMetricSeries,
  queryTargetMetricRange,
  type MetricRangePoint,
  type MetricRangeSeries
} from '@/api/monitoring'

export type MetricFieldType = 'number' | 'string' | 'time'

export interface TemplateMetricField {
  field: string
  title: string
  type: MetricFieldType
}

export interface TemplateMetricGroup {
  key: string
  title: string
  fields: TemplateMetricField[]
}

export interface MetricLatestPoint {
  name: string
  value?: number
  text?: string
  timestamp?: number
}

interface YamlI18nNode {
  [key: string]: any
}

function normalizeList(payload: any): { items: any[]; total: number } {
  if (Array.isArray(payload)) return { items: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { items: payload.items, total: Number(payload.total) || payload.items.length }
  return { items: [], total: 0 }
}

export function pickI18nText(value: any, locale = 'zh-CN', fallback = ''): string {
  if (typeof value === 'string') return value.trim() || fallback
  if (!value || typeof value !== 'object') return fallback
  const node = value as YamlI18nNode
  return String(node[locale] || node['zh-CN'] || node['en-US'] || fallback).trim() || fallback
}

export function normalizeMetricToken(raw: string): string {
  let token = String(raw || '').trim().toLowerCase()
  if (!token) return 'unknown'
  token = token.replace(/[^a-z0-9_]/g, '_').replace(/^_+|_+$/g, '')
  if (!token) return 'unknown'
  if (/^[0-9]/.test(token)) token = `m_${token}`
  return token
}

function toFieldType(raw: any): MetricFieldType {
  if (raw === 1 || raw === '1' || String(raw).toLowerCase() === 'string') return 'string'
  if (raw === 2 || raw === '2' || String(raw).toLowerCase() === 'time') return 'time'
  return 'number'
}

export function parseTemplateMetricGroups(templateContent: string, locale = 'zh-CN'): TemplateMetricGroup[] {
  try {
    const root = (yaml.load(templateContent || '') || {}) as any
    const metrics = Array.isArray(root?.metrics) ? root.metrics : []
    const out: TemplateMetricGroup[] = []
    for (const metric of metrics) {
      const key = String(metric?.name || '').trim()
      if (!key) continue
      const title = pickI18nText(metric?.i18n || metric?.name, locale, key)
      const fieldsRaw = Array.isArray(metric?.fields) ? metric.fields : []
      const fields: TemplateMetricField[] = []
      for (const f of fieldsRaw) {
        const field = String(f?.field || '').trim()
        if (!field) continue
        const fieldTitle = pickI18nText(f?.i18n || f?.name, locale, field)
        fields.push({
          field,
          title: fieldTitle,
          type: toFieldType(f?.type)
        })
      }
      if (!fields.length) continue
      out.push({ key, title, fields })
    }
    return out
  } catch {
    return []
  }
}

export async function fetchSeriesNames(monitorId: number): Promise<string[]> {
  if (!monitorId) return []
  const now = dayjs()
  const from = now.subtract(7, 'day').unix()
  const to = now.unix()
  const res = await getTargetMetricSeries(monitorId, { from, to })
  const parsed = normalizeList((res as any)?.data || res)
  const names = new Set<string>()
  for (const item of parsed.items || []) {
    const name = String((item as any)?.__name__ || '').trim()
    if (name) names.add(name)
  }
  return Array.from(names).sort()
}

export function resolveMetricName(
  app: string,
  groupKey: string,
  field: string,
  fieldType: MetricFieldType,
  seriesNames: string[]
): string {
  const names = new Set(seriesNames.map((item) => String(item || '').trim()).filter(Boolean))
  if (!names.size) {
    if (fieldType === 'string') return String(field || '').trim()
    return ''
  }

  const candidates: string[] = []
  const normGroup = normalizeMetricToken(groupKey)
  const normField = normalizeMetricToken(field)

  const pushCandidate = (name: string) => {
    const key = String(name || '').trim()
    if (!key || candidates.includes(key)) return
    candidates.push(key)
  }

  pushCandidate(field)
  pushCandidate(`${normGroup}_${normField}`)

  if (fieldType === 'string') {
    pushCandidate(`${field}_ok`)
    pushCandidate(`${normGroup}_${normField}_ok`)
  }

  if (field === 'success') {
    if (app) pushCandidate(`${normalizeMetricToken(app)}_server_up`)
    pushCandidate('server_up')
  }

  for (const item of candidates) {
    if (names.has(item)) return item
  }

  const suffixNeedle = `_${field}`
  const suffixMatches = seriesNames.filter((item) => String(item).endsWith(suffixNeedle))
  if (suffixMatches.length === 1) return suffixMatches[0]

  if (fieldType === 'string') {
    const okSuffixNeedle = `_${field}_ok`
    const okSuffixMatches = seriesNames.filter((item) => String(item).endsWith(okSuffixNeedle))
    if (okSuffixMatches.length === 1) return okSuffixMatches[0]
    // 字符串字段通常不会写入时序库，兜底使用原字段名走 latest 接口。
    return field
  }

  return ''
}

export function resolveQueryStep(rangeSeconds: number, intervalSeconds = 60): number {
  const interval = Math.max(intervalSeconds || 60, 15)
  if (rangeSeconds <= 3600) return Math.max(15, Math.min(interval, 60))
  if (rangeSeconds <= 86400) return Math.max(60, Math.min(interval, 300))
  if (rangeSeconds <= 7 * 86400) return 300
  return 900
}

export async function fetchLatestByNames(
  monitorId: number,
  names: string[],
  intervalSeconds = 60
): Promise<Record<string, MetricLatestPoint>> {
  const unique = Array.from(new Set(names.map((item) => String(item || '').trim()).filter(Boolean)))
  if (!monitorId || !unique.length) return {}

  const out: Record<string, MetricLatestPoint> = {}
  const now = dayjs()
  const lookbackSeconds = Math.max(3600, Math.max(intervalSeconds, 30) * 20)
  const from = now.subtract(lookbackSeconds, 'second').unix()
  const to = now.unix()
  const step = resolveQueryStep(lookbackSeconds, intervalSeconds)

  try {
    const res = await getTargetMetricLatest(monitorId, {
      names: unique.join(','),
      from,
      to,
      step
    })
    const parsed = normalizeList((res as any)?.data || res)
    if (parsed.items.length) {
      for (const item of parsed.items || []) {
        const name = String((item as any)?.name || '').trim()
        if (!name) continue
        const ts = Number((item as any)?.timestamp)
        const val = Number((item as any)?.value)
        const textRaw = (item as any)?.text
        const text = textRaw === undefined || textRaw === null ? '' : String(textRaw)
        out[name] = {
          name,
          value: Number.isFinite(val) ? val : undefined,
          text: text.trim() ? text : undefined,
          timestamp: Number.isFinite(ts) && ts > 0 ? ts : undefined
        }
      }
      return out
    }
  } catch {
    // fallback to query-range for compatibility with old manager
  }

  const res = await queryTargetMetricRange(monitorId, {
    names: unique.join(','),
    from,
    to,
    step
  })
  const parsed = normalizeList((res as any)?.data || res)

  for (const item of parsed.items || []) {
    const name = String((item as any)?.name || (item as any)?.labels?.__name__ || '').trim()
    if (!name) continue
    const points = Array.isArray((item as any)?.points) ? (item as any).points : []
    let latestTs = 0
    let latestVal: number | undefined = undefined
    for (const point of points) {
      const ts = Number((point as any)?.timestamp)
      const val = Number((point as any)?.value)
      if (!Number.isFinite(ts) || !Number.isFinite(val)) continue
      if (ts >= latestTs) {
        latestTs = ts
        latestVal = val
      }
    }
    out[name] = {
      name,
      value: latestVal,
      timestamp: latestTs > 0 ? latestTs : undefined
    }
  }

  return out
}

export async function fetchTrendSeries(
  monitorId: number,
  metricName: string,
  fromUnix: number,
  toUnix: number,
  intervalSeconds = 60
): Promise<MetricRangePoint[]> {
  const name = String(metricName || '').trim()
  if (!monitorId || !name) return []
  const range = Math.max(toUnix - fromUnix, 60)
  const step = resolveQueryStep(range, intervalSeconds)
  const res = await queryTargetMetricRange(monitorId, {
    name,
    from: fromUnix,
    to: toUnix,
    step
  })
  const parsed = normalizeList((res as any)?.data || res)
  const all = parsed.items as MetricRangeSeries[]
  const one = all.find((item) => String(item?.name || '').trim() === name) || all[0]
  if (!one?.points?.length) return []
  return one.points
    .map((point) => ({ timestamp: Number(point.timestamp), value: Number(point.value) }))
    .filter((point) => Number.isFinite(point.timestamp) && Number.isFinite(point.value))
    .sort((a, b) => a.timestamp - b.timestamp)
}

export function formatMetricValue(value?: number): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '-'
  if (Object.is(value, -0)) return '0'

  if (Number.isInteger(value)) return String(value)

  const abs = Math.abs(value)
  let digits = 3
  if (abs > 0 && abs < 1) digits = 6
  if (abs >= 1 && abs < 100) digits = 4
  if (abs >= 100) digits = 2

  const text = value.toFixed(digits)
  return text.replace(/\.?0+$/, '')
}

export function computeMetricStatus(
  metricName: string,
  latest: MetricLatestPoint | undefined,
  intervalSeconds: number
): 'normal' | 'abnormal' | 'unknown' {
  if (!latest?.timestamp) return 'unknown'
  const staleMs = Math.max(intervalSeconds || 60, 30) * 2 * 1000
  if (Date.now() - latest.timestamp > staleMs) return 'unknown'

  const key = String(metricName || '').toLowerCase()
  if (latest.value !== undefined && Number.isFinite(latest.value)) {
    if (key.endsWith('_ok') || key.endsWith('_up')) {
      return latest.value >= 0.5 ? 'normal' : 'abnormal'
    }
    return 'normal'
  }

  const text = String(latest.text || '').trim().toLowerCase()
  if (!text) return 'unknown'
  if (key.endsWith('_ok') || key.endsWith('_up')) {
    if (['ok', 'true', 'yes', 'up', 'online', 'connected', 'success', 'master'].includes(text)) return 'normal'
    if (['fail', 'failed', 'false', 'no', 'down', 'offline', 'disconnected', 'error', 'err'].includes(text)) return 'abnormal'
  }
  return 'normal'
}

export function buildLinePolyline(points: MetricRangePoint[], width = 640, height = 260): string {
  if (!points.length) return ''
  const left = 24
  const right = 20
  const top = 20
  const bottom = 28
  const innerW = width - left - right
  const innerH = height - top - bottom
  const sorted = [...points].sort((a, b) => a.timestamp - b.timestamp)
  const minTs = sorted[0].timestamp
  const maxTs = sorted[sorted.length - 1].timestamp
  const tsRange = Math.max(maxTs - minTs, 1)
  const values = sorted.map((point) => point.value)
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const valueRange = Math.max(maxVal - minVal, 1)

  return sorted
    .map((point) => {
      const x = left + ((point.timestamp - minTs) / tsRange) * innerW
      const y = top + (1 - (point.value - minVal) / valueRange) * innerH
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

export interface BarRect {
  x: number
  y: number
  width: number
  height: number
}

export function buildBarRects(points: MetricRangePoint[], width = 640, height = 260, maxBars = 80): BarRect[] {
  if (!points.length) return []
  const sorted = [...points].sort((a, b) => a.timestamp - b.timestamp)
  const step = Math.max(1, Math.ceil(sorted.length / maxBars))
  const sampled: MetricRangePoint[] = []
  for (let i = 0; i < sorted.length; i += step) {
    sampled.push(sorted[i])
  }

  const left = 24
  const right = 20
  const top = 20
  const bottom = 28
  const innerW = width - left - right
  const innerH = height - top - bottom

  const values = sampled.map((point) => point.value)
  const maxVal = Math.max(...values, 1)
  const barWidth = Math.max(2, innerW / Math.max(sampled.length, 1) - 2)

  return sampled.map((point, index) => {
    const x = left + index * (barWidth + 2)
    const barHeight = Math.max(1, (point.value / maxVal) * innerH)
    const y = top + (innerH - barHeight)
    return { x, y, width: barWidth, height: barHeight }
  })
}
