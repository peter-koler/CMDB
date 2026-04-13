export interface ModelOption {
  id: number
  name: string
  code: string
  keyFieldCodes: string[]
  fieldLabelMap: Record<string, string>
  orderedFieldCodes: string[]
}

export interface CiSelectionValue {
  id: number
  code: string
  display: string
  attributes: Record<string, any>
}

export interface MonitoringTargetFormDraft {
  name: string
  app: string
  target: string
  interval: number
  enabled: boolean
  ci_model_id?: number
  ci_id?: number
  ci_code?: string
  ci_display?: string
  ci_attributes?: Record<string, any>
  collector_id?: string
  pin_collector: boolean
  apply_default_alerts: boolean
  params: Record<string, any>
}

export function extractFieldLabelMap(formConfig: any[]): Record<string, string> {
  const out: Record<string, string> = {}
  const walk = (nodes: any[]) => {
    if (!Array.isArray(nodes)) return
    for (const node of nodes) {
      if (!node || typeof node !== 'object') continue
      const props = node.props && typeof node.props === 'object' ? node.props : {}
      const code = String(props.code || '').trim()
      const label = String(props.label || code).trim()
      if (code) out[code] = label || code
      if (Array.isArray(node.children) && node.children.length) walk(node.children)
    }
  }
  walk(formConfig)
  return out
}

export function extractOrderedFieldCodes(formConfig: any[]): string[] {
  const out: string[] = []
  const seen = new Set<string>()
  const walk = (nodes: any[]) => {
    if (!Array.isArray(nodes)) return
    for (const node of nodes) {
      if (!node || typeof node !== 'object') continue
      const props = node.props && typeof node.props === 'object' ? node.props : {}
      const code = String(props.code || '').trim()
      if (code && !seen.has(code)) {
        seen.add(code)
        out.push(code)
      }
      if (Array.isArray(node.children) && node.children.length) walk(node.children)
    }
  }
  walk(formConfig)
  return out
}

export function buildCiSelectionValue(item: any, modelMeta?: ModelOption): CiSelectionValue {
  const attrs = item?.attributes && typeof item.attributes === 'object' ? item.attributes : {}
  const keyPairs: string[] = []
  if (modelMeta?.keyFieldCodes?.length) {
    for (const keyCode of modelMeta.keyFieldCodes) {
      const raw = attrs[keyCode]
      if (raw === undefined || raw === null || String(raw).trim() === '') continue
      keyPairs.push(String(raw))
    }
  }
  if (!keyPairs.length) {
    const fallbackKeys = ['name', 'hostname', 'host', 'ip']
    for (const key of fallbackKeys) {
      const raw = attrs[key]
      if (raw === undefined || raw === null || String(raw).trim() === '') continue
      keyPairs.push(String(raw))
    }
  }
  const ciid = `CIID:${String(item?.id || '')}`
  const keyText = keyPairs.length ? keyPairs.join('｜') : String(item?.code || item?.id || '')
  return {
    id: Number(item?.id || 0),
    code: String(item?.code || item?.id || ''),
    display: `${keyText}｜${ciid}`,
    attributes: attrs
  }
}

export function createModelOption(item: any): ModelOption {
  const formConfig = Array.isArray(item?.form_config) ? item.form_config : []
  return {
    id: Number(item?.id || 0),
    name: String(item?.name || item?.code || item?.id || ''),
    code: String(item?.code || item?.id || ''),
    keyFieldCodes: Array.isArray(item?.key_field_codes)
      ? item.key_field_codes.map((entry: any) => String(entry || '').trim()).filter(Boolean)
      : [],
    fieldLabelMap: extractFieldLabelMap(formConfig),
    orderedFieldCodes: extractOrderedFieldCodes(formConfig)
  }
}

export function getMonitoringTargetDraftKey(mode: 'create' | 'edit', targetId?: number, category?: string): string {
  if (mode === 'edit' && targetId) return `monitoring-target-form:edit:${targetId}`
  return `monitoring-target-form:create:${String(category || 'default')}`
}

export function readMonitoringTargetDraft(key: string): Partial<MonitoringTargetFormDraft> | null {
  if (!key || typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

export function writeMonitoringTargetDraft(key: string, value: Partial<MonitoringTargetFormDraft>) {
  if (!key || typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    // ignore session storage errors
  }
}

export function removeMonitoringTargetDraft(key: string) {
  if (!key || typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(key)
  } catch {
    // ignore session storage errors
  }
}
