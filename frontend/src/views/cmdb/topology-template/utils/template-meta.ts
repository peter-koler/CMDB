import type { TopologyTemplate } from '@/api/cmdb-topology-template'

export interface ModelDef {
  key: string
  label: string
}

export interface RelationTypeOption {
  label: string
  value: 'RunsOn' | 'ConnectTo' | 'DependOn'
}

const nowIso = () => new Date().toISOString()

export const modelDefs: ModelDef[] = [
  { key: 'domain', label: '域名' },
  { key: 'load_balancer', label: '负载均衡' },
  { key: 'application', label: '应用' },
  { key: 'cloud_server', label: '云服务器' },
  { key: 'database', label: '数据库' },
  { key: 'middleware', label: '中间件' }
]

export const relationTypeOptions: RelationTypeOption[] = [
  { label: 'RunsOn', value: 'RunsOn' },
  { label: 'ConnectTo', value: 'ConnectTo' },
  { label: 'DependOn', value: 'DependOn' }
]

const modelTopologyEdges = [
  { source: 'domain', target: 'load_balancer' },
  { source: 'load_balancer', target: 'application' },
  { source: 'application', target: 'cloud_server' },
  { source: 'application', target: 'middleware' },
  { source: 'cloud_server', target: 'database' },
  { source: 'middleware', target: 'database' }
]

export const createEmptyTemplate = (): TopologyTemplate => ({
  id: `tpl-${Date.now()}`,
  name: '未命名模板',
  description: '',
  seedModels: ['cloud_server'],
  traverseDirection: 'both',
  allowedRelationTypes: ['RunsOn', 'ConnectTo', 'DependOn'],
  visibleModelKeys: modelDefs.map((item) => item.key),
  layers: [
    { id: `layer-${Date.now()}`, name: '新层级1', modelKeys: ['cloud_server'] }
  ],
  layoutDirection: 'horizontal',
  groupBy: 'idc',
  aggregateEnabled: true,
  aggregateThreshold: 4,
  updatedAt: nowIso()
})

export const buildModelTree = (seedModels: string[], modelByKey: Record<string, ModelDef>) => {
  const childMap: Record<string, string[]> = {}
  modelTopologyEdges.forEach((edge) => {
    if (!childMap[edge.source]) childMap[edge.source] = []
    childMap[edge.source].push(edge.target)
  })

  const roots = seedModels.length > 0 ? seedModels : ['cloud_server']

  const buildNode = (modelKey: string, depth: number, chain: string[]): any => {
    if (depth > 8 || chain.includes(modelKey)) {
      return { key: modelKey, title: modelByKey[modelKey]?.label || modelKey, isLeaf: true }
    }
    return {
      key: modelKey,
      title: modelByKey[modelKey]?.label || modelKey,
      children: (childMap[modelKey] || []).map((child) => buildNode(child, depth + 1, [...chain, modelKey]))
    }
  }

  const rootSet = new Set(roots)
  Object.keys(modelByKey).forEach((modelKey) => {
    rootSet.add(modelKey)
  })
  return Array.from(rootSet).map((key) => buildNode(key, 0, []))
}
