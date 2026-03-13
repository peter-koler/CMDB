<template>
  <div class="alert-topology">
    <a-space class="topology-actions">
      <a-button size="small" @click="zoomIn">放大</a-button>
      <a-button size="small" @click="zoomOut">缩小</a-button>
      <a-button size="small" @click="fitView">自适应</a-button>
    </a-space>

    <a-spin :spinning="loading">
      <div v-if="!ciId" class="topology-empty">暂无CI信息</div>
      <div v-else ref="graphContainer" class="graph-container" />
    </a-spin>

    <div v-if="selectedTopologyNode" class="node-panel">
      <div class="node-title">{{ selectedTopologyNode.name || '-' }}</div>
      <div class="node-sub">{{ selectedTopologyNode.code || '-' }}</div>
      <div class="node-meta">{{ selectedTopologyNode.model_name || '-' }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch, createApp, h } from 'vue'
import { Graph } from '@antv/g6'
import {
  AppstoreOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  HddOutlined,
  ApiOutlined,
  DeploymentUnitOutlined,
  ContainerOutlined,
  LaptopOutlined,
  GlobalOutlined
} from '@ant-design/icons-vue'
import { getInstanceDetail } from '@/api/ci'
import { getInstanceRelations } from '@/api/cmdb-relation'

const props = defineProps<{
  ciId?: number
}>()

const graphContainer = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const ciDetail = ref<any>(null)
const outRelations = ref<any[]>([])
const inRelations = ref<any[]>([])
const graphNodes = ref<any[]>([])
const graphEdges = ref<any[]>([])
const selectedTopologyNode = ref<any>(null)
let graph: any = null

const iconComponentMap: Record<string, any> = {
  AppstoreOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  HddOutlined,
  ApiOutlined,
  DeploymentUnitOutlined,
  ContainerOutlined,
  LaptopOutlined,
  GlobalOutlined
}

const builtinIconDataUrlCache: Record<string, string> = {}

const getAntdIconSvgMarkup = (iconName?: string) => {
  const iconComponent = iconComponentMap[iconName || ''] || AppstoreOutlined
  const container = document.createElement('div')
  const app = createApp({
    render() {
      return h(iconComponent, {
        style: {
          fontSize: '24px',
          color: '#1677ff'
        }
      })
    }
  })
  app.mount(container)
  const svg = container.querySelector('svg') as SVGElement | null
  if (!svg) {
    app.unmount()
    return ''
  }
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  svg.setAttribute('width', '24')
  svg.setAttribute('height', '24')
  svg.setAttribute('viewBox', svg.getAttribute('viewBox') || '64 64 896 896')
  svg.setAttribute('fill', 'currentColor')
  svg.style.color = '#1677ff'
  svg.style.display = 'block'
  const content = svg.outerHTML
  app.unmount()
  return content
}

const toSvgBase64DataUrl = (svg: string) => {
  const utf8 = unescape(encodeURIComponent(svg))
  const base64 = window.btoa(utf8)
  return `data:image/svg+xml;base64,${base64}`
}

const getBuiltinIconDataUrl = (iconName?: string) => {
  const cacheKey = iconName || 'AppstoreOutlined'
  if (builtinIconDataUrlCache[cacheKey]) {
    return builtinIconDataUrlCache[cacheKey]
  }
  const svg = getAntdIconSvgMarkup(cacheKey)
  const dataUrl = svg ? toSvgBase64DataUrl(svg) : ''
  builtinIconDataUrlCache[cacheKey] = dataUrl
  return dataUrl
}

const getNodeIconSrc = (node: any) => {
  if (node.model_icon_url) return node.model_icon_url
  return getBuiltinIconDataUrl(node.model_icon)
}

const getNodeDisplayText = (node: any) => {
  if (Array.isArray(node.display_subtitles) && node.display_subtitles.length > 0) {
    return node.display_subtitles.filter(Boolean).join(' | ')
  }
  return node.display_title || node.name || '-'
}

const applyGraphData = (data: { nodes: any[]; edges: any[] }) => {
  if (!graph) return
  if (typeof graph.changeData === 'function') {
    graph.changeData(data)
    return
  }
  if (typeof graph.setData === 'function') {
    graph.setData(data)
    if (typeof graph.render === 'function') graph.render()
    else if (typeof graph.draw === 'function') graph.draw()
  }
}

const renderGraph = () => {
  if (!graph) return
  const nodes = graphNodes.value.map((node) => ({
    id: String(node.id),
    type: 'image',
    draggable: true,
    model_id: node.model_id,
    style: {
      img: getNodeIconSrc(node),
      src: getNodeIconSrc(node),
      size: node.is_center ? 40 : 36,
      lineWidth: 0,
      labelText: getNodeDisplayText(node),
      labelPlacement: 'bottom',
      labelFill: '#1f1f1f',
      labelFontSize: 12
    },
    label: getNodeDisplayText(node)
  }))

  const edges = graphEdges.value.map((edge, index) => ({
    id: String(edge.id || index),
    source: String(edge.source),
    target: String(edge.target),
    style: {
      stroke: edge.direction === 'bidirectional' ? '#52c41a' : '#91d5ff',
      lineDash: edge.source_type === 'reference' ? [5, 5] : undefined,
      endArrow: edge.direction === 'directed',
      labelText: edge.relation_type_name || ''
    },
    label: edge.relation_type_name || ''
  }))

  applyGraphData({ nodes, edges })
}

const initGraph = () => {
  if (!graphContainer.value) return
  if (graph) {
    graph.destroy()
    graph = null
  }
  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: 420,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    defaultNode: {
      size: 36,
      style: { lineWidth: 0 },
      labelCfg: {
        style: {
          fill: '#1f1f1f',
          fontSize: 12
        },
        position: 'bottom'
      }
    },
    defaultEdge: {
      type: 'cubic-horizontal',
      style: {
        stroke: '#91d5ff',
        lineWidth: 2,
        endArrow: true
      }
    },
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeSpacing: 50,
      linkDistance: 150
    }
  } as any)

  graph.on('node:click', (evt: any) => {
    const node = evt?.item || evt?.target
    if (node) {
      const model = typeof node.getModel === 'function' ? node.getModel() : node
      const targetNode = graphNodes.value.find((item: any) => String(item.id) === String(model.id)) || null
      selectedTopologyNode.value = targetNode
    }
  })

  graph.on('canvas:click', () => {
    selectedTopologyNode.value = null
  })
}

const buildTopologyGraphData = () => {
  if (!ciDetail.value) return
  const nodes: any[] = []
  const edges: any[] = []
  const nodeIds = new Set<number>()

  nodes.push({
    id: ciDetail.value.id,
    name: ciDetail.value.name,
    code: ciDetail.value.code,
    model_id: ciDetail.value.model_id,
    model_icon: ciDetail.value.model?.icon || 'AppstoreOutlined',
    model_icon_url: ciDetail.value.model?.icon_url || '',
    display_title: ciDetail.value.name || '',
    display_subtitles: [],
    model_name: ciDetail.value.model?.name || '',
    is_center: true
  })
  nodeIds.add(ciDetail.value.id)

  outRelations.value.forEach((rel: any) => {
    if (!nodeIds.has(rel.target_ci_id)) {
      nodes.push({
        id: rel.target_ci_id,
        name: rel.target_ci_name,
        code: rel.target_ci_code,
        model_id: rel.target_ci_model_id,
        model_icon: rel.target_model_icon || 'AppstoreOutlined',
        model_icon_url: rel.target_model_icon_url || '',
        display_title: rel.target_display_title || rel.target_ci_name,
        display_subtitles: rel.target_display_subtitles || [],
        model_name: rel.target_ci_model_name,
        is_center: false
      })
      nodeIds.add(rel.target_ci_id)
    }
    edges.push({
      id: `out_${rel.id}`,
      source: ciDetail.value.id,
      target: rel.target_ci_id,
      relation_type_name: rel.relation_type_name,
      source_type: rel.source_type,
      direction: 'directed'
    })
  })

  inRelations.value.forEach((rel: any) => {
    if (!nodeIds.has(rel.source_ci_id)) {
      nodes.push({
        id: rel.source_ci_id,
        name: rel.source_ci_name,
        code: rel.source_ci_code,
        model_id: rel.source_ci_model_id,
        model_icon: rel.source_model_icon || 'AppstoreOutlined',
        model_icon_url: rel.source_model_icon_url || '',
        display_title: rel.source_display_title || rel.source_ci_name,
        display_subtitles: rel.source_display_subtitles || [],
        model_name: rel.source_ci_model_name,
        is_center: false
      })
      nodeIds.add(rel.source_ci_id)
    }
    edges.push({
      id: `in_${rel.id}`,
      source: rel.source_ci_id,
      target: ciDetail.value.id,
      relation_type_name: rel.relation_type_name,
      source_type: rel.source_type,
      direction: 'directed'
    })
  })

  graphNodes.value = nodes
  graphEdges.value = edges
  selectedTopologyNode.value = nodes.find((item: any) => item.is_center) || null
}

const loadTopology = async () => {
  const id = Number(props.ciId)
  if (!Number.isFinite(id) || id <= 0) {
    ciDetail.value = null
    outRelations.value = []
    inRelations.value = []
    graphNodes.value = []
    graphEdges.value = []
    selectedTopologyNode.value = null
    if (graph) graph.clear()
    return
  }
  loading.value = true
  try {
    const [detailRes, relationRes] = await Promise.all([
      getInstanceDetail(id),
      getInstanceRelations(id, { depth: 2 })
    ])
    ciDetail.value = (detailRes as any)?.data || null
    outRelations.value = (relationRes as any)?.data?.out_relations || []
    inRelations.value = (relationRes as any)?.data?.in_relations || []
    buildTopologyGraphData()
    await nextTick()
    if (!graph) initGraph()
    renderGraph()
  } finally {
    loading.value = false
  }
}

const zoomIn = () => {
  if (!graph) return
  const currentZoom = typeof graph.getZoom === 'function' ? graph.getZoom() : 1
  if (typeof graph.zoomTo === 'function') graph.zoomTo(currentZoom * 1.2)
  else if (typeof graph.zoomBy === 'function') graph.zoomBy(1.2)
}

const zoomOut = () => {
  if (!graph) return
  const currentZoom = typeof graph.getZoom === 'function' ? graph.getZoom() : 1
  if (typeof graph.zoomTo === 'function') graph.zoomTo(currentZoom * 0.8)
  else if (typeof graph.zoomBy === 'function') graph.zoomBy(0.8)
}

const fitView = () => {
  if (!graph) return
  if (typeof graph.fitView === 'function') graph.fitView()
  else if (typeof graph.fitCenter === 'function') graph.fitCenter()
}

const containerWidth = computed(() => graphContainer.value?.clientWidth || 0)

watch(
  () => [props.ciId, containerWidth.value],
  () => {
    loadTopology()
  },
  { immediate: true }
)

onMounted(() => {
  if (props.ciId) loadTopology()
})

onUnmounted(() => {
  if (graph) {
    graph.destroy()
    graph = null
  }
})
</script>

<style scoped>
.alert-topology {
  position: relative;
  min-height: 320px;
}

.topology-actions {
  margin-bottom: 8px;
}

.graph-container {
  width: 100%;
  height: 420px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

.topology-empty {
  text-align: center;
  color: #8c8c8c;
  padding: 80px 0;
}

.node-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fafafa;
}

.node-title {
  font-weight: 600;
}

.node-sub,
.node-meta {
  color: #8c8c8c;
  font-size: 12px;
}
</style>
