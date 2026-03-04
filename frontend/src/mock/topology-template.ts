export type TraverseDirection = 'up' | 'down' | 'both'
export type LayoutDirection = 'horizontal' | 'vertical'
export type GroupByKey = 'idc' | 'subnet' | 'owner'

export interface ModelDef {
  key: string
  label: string
}

export interface CiNode {
  id: string
  name: string
  modelKey: string
  status: 'OK' | 'WARN' | 'ALARM'
  idc: string
  subnet: string
  owner: string
}

export interface RelationEdge {
  id: string
  source: string
  target: string
  type: 'RunsOn' | 'ConnectTo' | 'DependOn'
}

export interface LayerRule {
  id: string
  name: string
  modelKeys: string[]
}

export interface TopologyTemplate {
  id: string
  name: string
  description: string
  seedModels: string[]
  traverseDirection: TraverseDirection
  allowedRelationTypes: Array<RelationEdge['type']>
  visibleModelKeys: string[]
  layers: LayerRule[]
  layoutDirection: LayoutDirection
  groupBy: GroupByKey
  aggregateEnabled: boolean
  aggregateThreshold: number
  updatedAt: string
}

const STORAGE_KEY = 'cmdb_topology_templates'

export const modelDefs: ModelDef[] = [
  { key: 'domain', label: '域名' },
  { key: 'load_balancer', label: '负载均衡' },
  { key: 'application', label: '应用' },
  { key: 'cloud_server', label: '云服务器' },
  { key: 'database', label: '数据库' },
  { key: 'middleware', label: '中间件' }
]

export const relationTypeOptions: Array<{ label: string; value: RelationEdge['type'] }> = [
  { label: 'RunsOn', value: 'RunsOn' },
  { label: 'ConnectTo', value: 'ConnectTo' },
  { label: 'DependOn', value: 'DependOn' }
]

export const modelTopologyEdges = [
  { source: 'domain', target: 'load_balancer' },
  { source: 'load_balancer', target: 'application' },
  { source: 'application', target: 'cloud_server' },
  { source: 'application', target: 'middleware' },
  { source: 'cloud_server', target: 'database' },
  { source: 'middleware', target: 'database' }
]

export const mockNodes: CiNode[] = [
  { id: 'd-1', name: 'api.shop.example.com', modelKey: 'domain', status: 'OK', idc: 'IDC-A', subnet: '10.10.1.0/24', owner: 'Team-A' },
  { id: 'd-2', name: 'pay.shop.example.com', modelKey: 'domain', status: 'OK', idc: 'IDC-B', subnet: '10.20.1.0/24', owner: 'Team-B' },
  { id: 'lb-1', name: 'SLB-Order', modelKey: 'load_balancer', status: 'OK', idc: 'IDC-A', subnet: '10.10.1.0/24', owner: 'Team-A' },
  { id: 'lb-2', name: 'SLB-Payment', modelKey: 'load_balancer', status: 'WARN', idc: 'IDC-B', subnet: '10.20.1.0/24', owner: 'Team-B' },
  { id: 'app-1', name: 'order-api', modelKey: 'application', status: 'OK', idc: 'IDC-A', subnet: '10.10.2.0/24', owner: 'Team-A' },
  { id: 'app-2', name: 'order-worker', modelKey: 'application', status: 'WARN', idc: 'IDC-A', subnet: '10.10.2.0/24', owner: 'Team-A' },
  { id: 'app-3', name: 'pay-api', modelKey: 'application', status: 'OK', idc: 'IDC-B', subnet: '10.20.2.0/24', owner: 'Team-B' },
  { id: 'srv-1', name: 'ecs-order-01', modelKey: 'cloud_server', status: 'OK', idc: 'IDC-A', subnet: '10.10.3.0/24', owner: 'Team-A' },
  { id: 'srv-2', name: 'ecs-order-02', modelKey: 'cloud_server', status: 'OK', idc: 'IDC-A', subnet: '10.10.3.0/24', owner: 'Team-A' },
  { id: 'srv-3', name: 'ecs-order-03', modelKey: 'cloud_server', status: 'ALARM', idc: 'IDC-A', subnet: '10.10.3.0/24', owner: 'Team-A' },
  { id: 'srv-4', name: 'ecs-pay-01', modelKey: 'cloud_server', status: 'OK', idc: 'IDC-B', subnet: '10.20.3.0/24', owner: 'Team-B' },
  { id: 'srv-5', name: 'ecs-pay-02', modelKey: 'cloud_server', status: 'WARN', idc: 'IDC-B', subnet: '10.20.3.0/24', owner: 'Team-B' },
  { id: 'mw-1', name: 'kafka-order', modelKey: 'middleware', status: 'OK', idc: 'IDC-A', subnet: '10.10.4.0/24', owner: 'Team-A' },
  { id: 'mw-2', name: 'redis-pay', modelKey: 'middleware', status: 'OK', idc: 'IDC-B', subnet: '10.20.4.0/24', owner: 'Team-B' },
  { id: 'db-1', name: 'order-mysql-main', modelKey: 'database', status: 'OK', idc: 'IDC-A', subnet: '10.10.5.0/24', owner: 'DBA-A' },
  { id: 'db-2', name: 'order-mysql-rep', modelKey: 'database', status: 'OK', idc: 'IDC-A', subnet: '10.10.5.0/24', owner: 'DBA-A' },
  { id: 'db-3', name: 'pay-mysql-main', modelKey: 'database', status: 'ALARM', idc: 'IDC-B', subnet: '10.20.5.0/24', owner: 'DBA-B' }
]

export const mockEdges: RelationEdge[] = [
  { id: 'r-1', source: 'd-1', target: 'lb-1', type: 'ConnectTo' },
  { id: 'r-2', source: 'd-2', target: 'lb-2', type: 'ConnectTo' },
  { id: 'r-3', source: 'lb-1', target: 'app-1', type: 'ConnectTo' },
  { id: 'r-4', source: 'lb-1', target: 'app-2', type: 'ConnectTo' },
  { id: 'r-5', source: 'lb-2', target: 'app-3', type: 'ConnectTo' },
  { id: 'r-6', source: 'app-1', target: 'srv-1', type: 'RunsOn' },
  { id: 'r-7', source: 'app-1', target: 'srv-2', type: 'RunsOn' },
  { id: 'r-8', source: 'app-2', target: 'srv-3', type: 'RunsOn' },
  { id: 'r-9', source: 'app-3', target: 'srv-4', type: 'RunsOn' },
  { id: 'r-10', source: 'app-3', target: 'srv-5', type: 'RunsOn' },
  { id: 'r-11', source: 'app-1', target: 'mw-1', type: 'DependOn' },
  { id: 'r-12', source: 'app-3', target: 'mw-2', type: 'DependOn' },
  { id: 'r-13', source: 'srv-1', target: 'db-1', type: 'DependOn' },
  { id: 'r-14', source: 'srv-2', target: 'db-2', type: 'DependOn' },
  { id: 'r-15', source: 'srv-4', target: 'db-3', type: 'DependOn' },
  { id: 'r-16', source: 'mw-1', target: 'db-1', type: 'DependOn' },
  { id: 'r-17', source: 'mw-2', target: 'db-3', type: 'DependOn' }
]

const nowIso = () => new Date().toISOString()

const templateA = (): TopologyTemplate => ({
  id: 'tpl-core-service',
  name: '核心交易链路',
  description: '从云服务器和应用出发，查看核心交易依赖路径',
  seedModels: ['cloud_server', 'application'],
  traverseDirection: 'both',
  allowedRelationTypes: ['RunsOn', 'ConnectTo', 'DependOn'],
  visibleModelKeys: modelDefs.map((item) => item.key),
  layers: [
    { id: 'l1', name: '接入层', modelKeys: ['domain', 'load_balancer'] },
    { id: 'l2', name: '应用层', modelKeys: ['application', 'middleware'] },
    { id: 'l3', name: '计算层', modelKeys: ['cloud_server'] },
    { id: 'l4', name: '数据层', modelKeys: ['database'] }
  ],
  layoutDirection: 'horizontal',
  groupBy: 'idc',
  aggregateEnabled: true,
  aggregateThreshold: 4,
  updatedAt: nowIso()
})

const templateB = (): TopologyTemplate => ({
  id: 'tpl-network-view',
  name: '网络入口拓扑',
  description: '聚焦域名、负载均衡、应用的入口路径',
  seedModels: ['domain'],
  traverseDirection: 'down',
  allowedRelationTypes: ['ConnectTo'],
  visibleModelKeys: ['domain', 'load_balancer', 'application'],
  layers: [
    { id: 'n1', name: '入口层', modelKeys: ['domain', 'load_balancer'] },
    { id: 'n2', name: '服务层', modelKeys: ['application'] }
  ],
  layoutDirection: 'vertical',
  groupBy: 'owner',
  aggregateEnabled: true,
  aggregateThreshold: 3,
  updatedAt: nowIso()
})

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

const normalizeTemplate = (template: TopologyTemplate): TopologyTemplate => ({
  ...template,
  visibleModelKeys: Array.from(new Set(template.visibleModelKeys)),
  seedModels: Array.from(new Set(template.seedModels)),
  allowedRelationTypes: Array.from(new Set(template.allowedRelationTypes)),
  layers: template.layers.map((layer) => ({
    ...layer,
    modelKeys: Array.from(new Set(layer.modelKeys))
  })),
  aggregateThreshold: Math.max(2, Number(template.aggregateThreshold || 2)),
  updatedAt: nowIso()
})

const readStorage = (): TopologyTemplate[] => {
  if (typeof window === 'undefined') return [templateA(), templateB()]
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as TopologyTemplate[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const writeStorage = (templates: TopologyTemplate[]) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(templates))
}

export const listTopologyTemplates = (): TopologyTemplate[] => {
  const templates = readStorage()
  if (templates.length > 0) return templates
  const defaults = [templateA(), templateB()]
  writeStorage(defaults)
  return defaults
}

export const getTopologyTemplate = (id: string): TopologyTemplate | undefined => {
  return listTopologyTemplates().find((item) => item.id === id)
}

export const upsertTopologyTemplate = (template: TopologyTemplate): TopologyTemplate[] => {
  const normalized = normalizeTemplate(template)
  const list = listTopologyTemplates()
  const index = list.findIndex((item) => item.id === normalized.id)
  if (index >= 0) {
    list[index] = normalized
  } else {
    list.unshift(normalized)
  }
  writeStorage(list)
  return list
}

export const deleteTopologyTemplate = (id: string): TopologyTemplate[] => {
  const next = listTopologyTemplates().filter((item) => item.id !== id)
  writeStorage(next)
  return next
}

export const cloneTopologyTemplate = (id: string): TopologyTemplate | undefined => {
  const source = getTopologyTemplate(id)
  if (!source) return undefined
  const next: TopologyTemplate = {
    ...source,
    id: `tpl-${Date.now()}`,
    name: `${source.name}-副本`,
    layers: source.layers.map((layer) => ({
      ...layer,
      id: `${layer.id}-${Date.now()}`
    })),
    updatedAt: nowIso()
  }
  upsertTopologyTemplate(next)
  return next
}

export const buildModelTree = (seedModels: string[], modelByKey: Record<string, ModelDef>) => {
  const childMap: Record<string, string[]> = {}
  modelTopologyEdges.forEach((edge) => {
    if (!childMap[edge.source]) {
      childMap[edge.source] = []
    }
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

  return roots.map((key) => buildNode(key, 0, []))
}

interface ExtractResult {
  nodes: CiNode[]
  edges: RelationEdge[]
  seedNodeIds: string[]
}

export const extractByTemplate = (template: TopologyTemplate, collapsedNodeIds?: Set<string>): ExtractResult => {
  const visibleModelSet = new Set(template.visibleModelKeys)
  const allowedTypeSet = new Set(template.allowedRelationTypes)

  const nodeById: Record<string, CiNode> = {}
  mockNodes.forEach((node) => {
    nodeById[node.id] = node
  })

  const adjacencyDown: Record<string, RelationEdge[]> = {}
  const adjacencyUp: Record<string, RelationEdge[]> = {}

  mockEdges.forEach((edge) => {
    if (!adjacencyDown[edge.source]) adjacencyDown[edge.source] = []
    if (!adjacencyUp[edge.target]) adjacencyUp[edge.target] = []
    adjacencyDown[edge.source].push(edge)
    adjacencyUp[edge.target].push(edge)
  })

  const seedNodeIds = mockNodes
    .filter((node) => template.seedModels.includes(node.modelKey) && visibleModelSet.has(node.modelKey))
    .map((node) => node.id)

  const visited = new Set<string>(seedNodeIds)
  const edgeMap = new Map<string, RelationEdge>()
  const queue = [...seedNodeIds]

  while (queue.length > 0) {
    const currentId = queue.shift() as string

    const visit = (edge: RelationEdge, neighborId: string) => {
      if (!allowedTypeSet.has(edge.type)) return
      const neighbor = nodeById[neighborId]
      if (!neighbor || !visibleModelSet.has(neighbor.modelKey)) return
      edgeMap.set(edge.id, edge)
      if (!visited.has(neighborId)) {
        visited.add(neighborId)
        queue.push(neighborId)
      }
    }

    if (template.traverseDirection === 'down' || template.traverseDirection === 'both') {
      ;(adjacencyDown[currentId] || []).forEach((edge) => visit(edge, edge.target))
    }

    if (template.traverseDirection === 'up' || template.traverseDirection === 'both') {
      ;(adjacencyUp[currentId] || []).forEach((edge) => visit(edge, edge.source))
    }
  }

  const nodes = Array.from(visited).map((id) => nodeById[id]).filter(Boolean)
  const edges = Array.from(edgeMap.values())

  if (!collapsedNodeIds || collapsedNodeIds.size === 0) {
    return { nodes, edges, seedNodeIds }
  }

  const downMap: Record<string, string[]> = {}
  edges.forEach((edge) => {
    if (!downMap[edge.source]) downMap[edge.source] = []
    downMap[edge.source].push(edge.target)
  })

  const hidden = new Set<string>()
  const stack = Array.from(collapsedNodeIds)
  while (stack.length > 0) {
    const root = stack.pop() as string
    const children = downMap[root] || []
    children.forEach((child) => {
      if (hidden.has(child)) return
      hidden.add(child)
      stack.push(child)
    })
  }

  const visibleIds = new Set(nodes.map((node) => node.id).filter((id) => !hidden.has(id)))
  return {
    seedNodeIds,
    nodes: nodes.filter((node) => visibleIds.has(node.id)),
    edges: edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
  }
}

export const buildRenderedGraphData = (template: TopologyTemplate, collapsedNodeIds?: Set<string>) => {
  const extracted = extractByTemplate(template, collapsedNodeIds)
  const groupBy = template.groupBy

  const layerOrderMap: Record<string, number> = {}
  template.layers.forEach((layer, layerIndex) => {
    layer.modelKeys.forEach((modelKey) => {
      layerOrderMap[modelKey] = layerIndex
    })
  })

  const groupMap = new Map<string, CiNode[]>()
  extracted.nodes.forEach((node) => {
    const key = `${String(node[groupBy] || 'unknown')}::${node.modelKey}`
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key)?.push(node)
  })

  const replacement: Record<string, string> = {}
  const aggregateNodes: Record<string, any> = {}

  if (template.aggregateEnabled) {
    Array.from(groupMap.entries()).forEach(([group, members]) => {
      if (members.length <= template.aggregateThreshold) return
      const first = members[0]
      if (!first) return
      // Seed 模型保持原始节点，避免模板入口被整体聚合成少量图标
      if (template.seedModels.includes(first.modelKey)) return
      const pureGroup = String(first[groupBy] || 'unknown')
      const id = `agg-${groupBy}-${pureGroup}-${first.modelKey}`
      aggregateNodes[id] = {
        id,
        nodeKind: 'aggregate',
        name: `${pureGroup}-${first.modelKey} (${members.length})`,
        modelKey: 'aggregate',
        status: members.some((m) => m.status !== 'OK') ? 'ALARM' : 'OK',
        [groupBy]: pureGroup
      }
      members.forEach((member) => {
        replacement[member.id] = id
      })
    })
  }

  const nodeMap: Record<string, any> = {}
  extracted.nodes.forEach((node) => {
    const repl = replacement[node.id]
    if (!repl) {
      nodeMap[node.id] = { ...node, nodeKind: 'instance' }
      return
    }
    nodeMap[repl] = aggregateNodes[repl]
  })

  const edgeMap = new Map<string, any>()
  extracted.edges.forEach((edge) => {
    const source = replacement[edge.source] || edge.source
    const target = replacement[edge.target] || edge.target
    if (source === target) return
    const key = `${source}-${target}-${edge.type}`
    if (!edgeMap.has(key)) {
      edgeMap.set(key, {
        id: `edge-${key}`,
        source,
        target,
        type: edge.type
      })
    }
  })

  const nodes = Object.values(nodeMap)
  const edges = Array.from(edgeMap.values())

  const layers = new Map<number, any[]>()
  nodes.forEach((node) => {
    const index = node.modelKey === 'aggregate'
      ? Math.max(template.layers.length, 1)
      : (layerOrderMap[node.modelKey] ?? template.layers.length)
    if (!layers.has(index)) layers.set(index, [])
    layers.get(index)?.push(node)
  })

  const sortedLayers = Array.from(layers.entries()).sort((a, b) => a[0] - b[0])
  const positionedNodes: any[] = []

  const mainGap = 280
  const crossGap = 94

  sortedLayers.forEach(([layerIndex, layerNodes]) => {
    layerNodes
      .sort((a: any, b: any) => String(a.name).localeCompare(String(b.name)))
      .forEach((node: any, rowIndex: number) => {
        const x = template.layoutDirection === 'horizontal' ? 120 + layerIndex * mainGap : 120 + rowIndex * crossGap
        const y = template.layoutDirection === 'horizontal' ? 80 + rowIndex * crossGap : 80 + layerIndex * mainGap
        positionedNodes.push({ ...node, x, y })
      })
  })

  const comboMap = new Map<string, any>()
  positionedNodes.forEach((node) => {
    if (node.nodeKind === 'aggregate') return
    const key = `combo-${groupBy}-${String(node[groupBy] || 'unknown')}`
    if (!comboMap.has(key)) {
      comboMap.set(key, {
        id: key,
        label: String(node[groupBy] || 'unknown'),
        style: {
          fill: 'rgba(22, 119, 255, 0.06)',
          stroke: 'rgba(22, 119, 255, 0.25)',
          lineWidth: 1
        }
      })
    }
  })

  return {
    extracted,
    nodes: positionedNodes,
    edges,
    combos: Array.from(comboMap.values())
  }
}
