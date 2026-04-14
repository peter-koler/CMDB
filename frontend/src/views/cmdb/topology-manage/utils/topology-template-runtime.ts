import type { TopologyTemplate } from '@/api/cmdb-topology-template'

export interface RuntimeModelMeta {
  id: number
  code: string
  name: string
}

export interface RuntimeRelationTypeMeta {
  id: number
  code: string
  name: string
}

export interface RuntimeTopologyNode {
  id: number | string
  name?: string
  code?: string
  model_id?: number
  model_name?: string
  model_icon?: string
  model_icon_url?: string
  display_title?: string
  display_subtitles?: string[]
  has_open_alert?: boolean
}

export interface RuntimeTopologyEdge {
  id: number | string
  source: number | string
  target: number | string
  relation_type_id?: number
  relation_type_name?: string
  direction?: string
}

export interface RenderNode {
  id: string
  nodeKind: 'instance' | 'aggregate'
  name: string
  primaryText: string
  modelKey: string
  modelId?: number
  modelIcon?: string
  modelIconUrl?: string
  status: 'RUNNING' | 'ALARM'
  hasOpenAlert?: boolean
  count?: number
  idc?: string
  subnet?: string
  owner?: string
}

export interface RenderEdge {
  id: string
  source: string
  target: string
  type: string
  direction?: string
}

export interface ExtractResult {
  nodes: RenderNode[]
  edges: RenderEdge[]
  seedNodeIds: string[]
}

interface BuildContext {
  modelById: Record<number, RuntimeModelMeta>
  relationTypeById: Record<number, RuntimeRelationTypeMeta>
}

const toNodeId = (value: number | string) => String(value)

const resolveModelCode = (node: RuntimeTopologyNode, context: BuildContext) => {
  const id = Number(node.model_id || 0)
  if (id > 0 && context.modelById[id]?.code) return context.modelById[id].code
  return 'unknown'
}

const resolveEdgeType = (edge: RuntimeTopologyEdge, context: BuildContext) => {
  const relId = Number(edge.relation_type_id || 0)
  if (relId > 0) {
    const rel = context.relationTypeById[relId]
    if (rel?.code) return rel.code
    if (rel?.name) return rel.name
  }
  return String(edge.relation_type_name || '') || 'relation'
}

export const extractByTemplate = (
  template: TopologyTemplate,
  rawNodes: RuntimeTopologyNode[],
  rawEdges: RuntimeTopologyEdge[],
  context: BuildContext,
  collapsedNodeIds?: Set<string>
): ExtractResult => {
  const nodeById: Record<string, RuntimeTopologyNode> = {}
  rawNodes.forEach((node) => {
    nodeById[toNodeId(node.id)] = node
  })

  const visibleModelSet = new Set(template.visibleModelKeys || [])
  const allowedRelationSet = new Set(template.allowedRelationTypes || [])

  const adjacencyDown: Record<string, RuntimeTopologyEdge[]> = {}
  const adjacencyUp: Record<string, RuntimeTopologyEdge[]> = {}

  rawEdges.forEach((edge) => {
    const source = toNodeId(edge.source)
    const target = toNodeId(edge.target)
    if (!adjacencyDown[source]) adjacencyDown[source] = []
    if (!adjacencyUp[target]) adjacencyUp[target] = []
    adjacencyDown[source].push(edge)
    adjacencyUp[target].push(edge)
  })

  const seedNodeIds = rawNodes
    .filter((node) => {
      const modelCode = resolveModelCode(node, context)
      if (!template.seedModels.includes(modelCode)) return false
      return visibleModelSet.size === 0 || visibleModelSet.has(modelCode)
    })
    .map((node) => toNodeId(node.id))

  const effectiveSeeds = seedNodeIds.length > 0
    ? seedNodeIds
    : rawNodes
        .filter((node) => {
          const modelCode = resolveModelCode(node, context)
          return visibleModelSet.size === 0 || visibleModelSet.has(modelCode)
        })
        .map((node) => toNodeId(node.id))

  const visited = new Set<string>(effectiveSeeds)
  const edgeMap = new Map<string, RenderEdge>()
  const queue = [...effectiveSeeds]

  while (queue.length > 0) {
    const currentId = queue.shift() as string

    const visit = (edge: RuntimeTopologyEdge, neighborId: string) => {
      const edgeType = resolveEdgeType(edge, context)
      if (allowedRelationSet.size > 0 && !allowedRelationSet.has(edgeType)) return
      const neighbor = nodeById[neighborId]
      if (!neighbor) return
      const neighborModelCode = resolveModelCode(neighbor, context)
      if (visibleModelSet.size > 0 && !visibleModelSet.has(neighborModelCode)) return

      const edgeId = `edge-${toNodeId(edge.id)}`
      edgeMap.set(edgeId, {
        id: edgeId,
        source: toNodeId(edge.source),
        target: toNodeId(edge.target),
        type: edgeType,
        direction: edge.direction
      })

      if (!visited.has(neighborId)) {
        visited.add(neighborId)
        queue.push(neighborId)
      }
    }

    if (template.traverseDirection === 'down' || template.traverseDirection === 'both') {
      ;(adjacencyDown[currentId] || []).forEach((edge) => visit(edge, toNodeId(edge.target)))
    }

    if (template.traverseDirection === 'up' || template.traverseDirection === 'both') {
      ;(adjacencyUp[currentId] || []).forEach((edge) => visit(edge, toNodeId(edge.source)))
    }
  }

  const nodes: RenderNode[] = Array.from(visited)
    .map((id) => {
      const raw = nodeById[id]
      if (!raw) return null
      const modelKey = resolveModelCode(raw, context)
      const subtitles = Array.isArray(raw.display_subtitles)
        ? raw.display_subtitles.map((item) => String(item || '').trim()).filter(Boolean)
        : []
      const primaryText = subtitles.join(' | ') || String(raw.display_title || raw.name || raw.code || '未配置关键属性')
      return {
        id,
        nodeKind: 'instance',
        name: String(raw.display_title || raw.name || raw.code || id),
        primaryText,
        modelKey,
        modelId: Number(raw.model_id || 0) || undefined,
        modelIcon: raw.model_icon || undefined,
        modelIconUrl: raw.model_icon_url || undefined,
        status: raw.has_open_alert ? 'ALARM' : 'RUNNING',
        hasOpenAlert: Boolean(raw.has_open_alert)
      }
    })
    .filter(Boolean) as RenderNode[]

  const edges = Array.from(edgeMap.values())

  if (!collapsedNodeIds || collapsedNodeIds.size === 0) {
    return { nodes, edges, seedNodeIds: effectiveSeeds }
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
    seedNodeIds: effectiveSeeds,
    nodes: nodes.filter((node) => visibleIds.has(node.id)),
    edges: edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
  }
}

export const buildRenderedGraphData = (
  template: TopologyTemplate,
  rawNodes: RuntimeTopologyNode[],
  rawEdges: RuntimeTopologyEdge[],
  context: BuildContext,
  collapsedNodeIds?: Set<string>
) => {
  const extracted = extractByTemplate(template, rawNodes, rawEdges, context, collapsedNodeIds)
  const groupBy = template.groupBy

  const layerOrderMap: Record<string, number> = {}
  template.layers.forEach((layer, layerIndex) => {
    layer.modelKeys.forEach((modelKey) => {
      layerOrderMap[modelKey] = layerIndex
    })
  })

  const groupMap = new Map<string, RenderNode[]>()
  extracted.nodes.forEach((node) => {
    const key = `default::${node.modelKey}`
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key)?.push(node)
  })

  const replacement: Record<string, string> = {}
  const aggregateNodes: Record<string, RenderNode> = {}

  if (template.aggregateEnabled) {
    Array.from(groupMap.entries()).forEach(([group, members]) => {
      if (members.length <= template.aggregateThreshold) return
      const first = members[0]
      if (!first) return
      if (template.seedModels.includes(first.modelKey)) return

      const pureGroup = String(groupBy || 'group')
      const id = `agg-${pureGroup}-${first.modelKey}`
      aggregateNodes[id] = {
        id,
        nodeKind: 'aggregate',
        name: `${first.modelKey}`,
        primaryText: `${first.modelKey} (${members.length})`,
        modelKey: 'aggregate',
        status: members.some((m) => m.status !== 'RUNNING') ? 'ALARM' : 'RUNNING',
        hasOpenAlert: members.some((m) => m.hasOpenAlert),
        count: members.length
      }
      members.forEach((member) => {
        replacement[member.id] = id
      })
    })
  }

  const nodeMap: Record<string, RenderNode> = {}
  extracted.nodes.forEach((node) => {
    const repl = replacement[node.id]
    if (!repl) {
      nodeMap[node.id] = node
      return
    }
    nodeMap[repl] = aggregateNodes[repl]
  })

  const edgeMap = new Map<string, RenderEdge>()
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
        type: edge.type,
        direction: edge.direction
      })
    }
  })

  return {
    extracted,
    nodes: Object.values(nodeMap),
    edges: Array.from(edgeMap.values()),
    combos: []
  }
}
