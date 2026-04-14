export type TopologyNodeLite = {
  id: string | number
}

export type TopologyEdgeLite = {
  id?: string | number
  source: string | number
  target: string | number
  direction?: string
}

export type TopologyBadgeStyle = {
  text: string
  placement: 'right-top'
  fill: string
  fontSize: number
  padding: [number, number]
  lineWidth: number
  stroke: string
  cursor: string
  opacity: number
  background: boolean
  fontWeight?: number
  offsetX?: number
  offsetY?: number
}

export type TopologyVisibilityResult<TNode, TEdge> = {
  nodes: TNode[]
  edges: TEdge[]
  collapsibleNodeIds: Set<string>
}

const toId = (value: string | number | null | undefined) => String(value ?? '')

const buildOutgoingAdjacency = (edges: TopologyEdgeLite[]) => {
  const outgoing = new Map<string, Set<string>>()

  const add = (from: string, to: string) => {
    if (!outgoing.has(from)) outgoing.set(from, new Set())
    outgoing.get(from)?.add(to)
  }

  edges.forEach((edge) => {
    const source = toId(edge.source)
    const target = toId(edge.target)
    if (!source || !target) return
    add(source, target)
    if (edge.direction !== 'directed') {
      add(target, source)
    }
  })

  return outgoing
}

const collectCollapsedDescendants = (rootId: string, outgoing: Map<string, Set<string>>) => {
  const hiddenNodeIds = new Set<string>()
  const visited = new Set<string>([rootId])
  const queue = [...(outgoing.get(rootId) || [])]

  while (queue.length) {
    const current = queue.shift() as string
    if (!current || visited.has(current)) continue
    visited.add(current)
    if (current === rootId) continue
    hiddenNodeIds.add(current)
    const children = outgoing.get(current)
    if (children?.size) {
      children.forEach((child) => {
        if (!visited.has(child)) queue.push(child)
      })
    }
  }

  return hiddenNodeIds
}

export const buildVisibleTopology = <TNode extends TopologyNodeLite, TEdge extends TopologyEdgeLite>(
  allNodes: TNode[],
  allEdges: TEdge[],
  collapsedNodeIds: Set<string>
): TopologyVisibilityResult<TNode, TEdge> => {
  const outgoing = buildOutgoingAdjacency(allEdges)
  const collapsibleNodeIds = new Set<string>()
  outgoing.forEach((children, nodeId) => {
    if (children.size > 0) collapsibleNodeIds.add(nodeId)
  })

  if (!collapsedNodeIds.size) {
    return {
      nodes: allNodes,
      edges: allEdges,
      collapsibleNodeIds
    }
  }

  const hiddenNodeIds = new Set<string>()
  collapsedNodeIds.forEach((collapsedId) => {
    const descendants = collectCollapsedDescendants(collapsedId, outgoing)
    descendants.forEach((id) => hiddenNodeIds.add(id))
  })

  const nodes = allNodes.filter((node) => !hiddenNodeIds.has(toId(node.id)))
  const visibleNodeIdSet = new Set(nodes.map((node) => toId(node.id)))
  const edges = allEdges.filter((edge) => {
    return visibleNodeIdSet.has(toId(edge.source)) && visibleNodeIdSet.has(toId(edge.target))
  })

  return {
    nodes,
    edges,
    collapsibleNodeIds
  }
}

export const buildNodeToggleBadges = (
  nodeId: string,
  collapsedNodeIds: Set<string>,
  collapsibleNodeIds: Set<string>
): TopologyBadgeStyle[] => {
  const canCollapse = collapsibleNodeIds.has(nodeId)
  const isCollapsed = collapsedNodeIds.has(nodeId)
  if (!canCollapse && !isCollapsed) return []
  const symbol = isCollapsed ? '+' : '-'

  return [{
    text: symbol,
    placement: 'right-top',
    fill: '#111111',
    fontSize: 18,
    fontWeight: 700,
    padding: [0, 0] as [number, number],
    lineWidth: 2.2,
    stroke: '#ffffff',
    cursor: 'pointer',
    opacity: 0.98,
    background: false,
    offsetX: 9,
    offsetY: -2
  }]
}

const parseShapeHint = (shape: any) => {
  const text = String(
    shape?.style?.text ??
    shape?.parsedStyle?.text ??
    shape?.attributes?.text ??
    shape?.config?.style?.text ??
    ''
  ).trim()

  const hint = [
    shape?.id,
    shape?.name,
    shape?.className,
    shape?.nodeName,
    shape?.config?.id,
    shape?.config?.name,
    shape?.parentNode?.id,
    shape?.parentNode?.name
  ].filter(Boolean).join(' ')

  return { text, hint }
}

export const resolveNodeToggleAction = (evt: any): 'expand' | 'collapse' | null => {
  const original = evt?.originalTarget
  if (!original) return null

  const current = parseShapeHint(original)
  const parent = parseShapeHint(original?.parentNode)
  const text = current.text || parent.text
  const hint = `${current.hint} ${parent.hint}`

  if (text === '+') return 'expand'
  if (text === '-') return 'collapse'
  if (hint.includes('badge-0') && text === '+') return 'expand'
  if (hint.includes('badge-0') && text === '-') return 'collapse'

  return null
}
