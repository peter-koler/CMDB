<template>
  <div class="app-page topology-page">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[12, 12]" class="topology-filter-row">
          <a-col :xs="24" :sm="12" :md="8" :lg="5">
            <a-form-item label="关键词">
              <a-input
                v-model:value="searchKeyword"
                placeholder="请输入关键属性值"
                allowClear
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="8" :lg="5">
            <a-form-item label="模型">
              <a-select
                v-model:value="searchModelIds"
                mode="multiple"
                placeholder="请选择模型（可多选）"
                style="width: 100%"
                allowClear
                :max-tag-count="2"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="8" :lg="5">
            <a-form-item label="起点CI">
              <a-select
                v-model:value="searchCiIds"
                mode="multiple"
                placeholder="按关键属性选择起点（可多选）"
                style="width: 100%"
                allowClear
                show-search
                option-filter-prop="label"
                :max-tag-count="2"
              >
                <a-select-option
                  v-for="ci in filteredCandidateCis"
                  :key="ci.id"
                  :value="ci.id"
                  :label="getCiDisplayText(ci)"
                >
                  {{ getCiDisplayText(ci) }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="8" :lg="4">
            <a-form-item label="深度">
              <a-input-number
                v-model:value="relationDepth"
                :min="1"
                :max="TOPOLOGY_DEPTH_LIMIT"
                :step="1"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="8" :lg="5">
            <a-form-item label="布局">
              <a-select v-model:value="layout" placeholder="布局算法" style="width: 100%">
                <a-select-option value="force">力导向</a-select-option>
                <a-select-option value="dagre">层级</a-select-option>
                <a-select-option value="circular">环形</a-select-option>
                <a-select-option value="grid">网格</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="[12, 12]" class="topology-action-row">
          <a-col :span="24">
            <a-form-item class="search-buttons">
              <a-space wrap>
                <a-button type="primary" @click="handleSearch">
                  <template #icon><SearchOutlined /></template>
                  搜索
                </a-button>
                <a-button @click="handleReset">
                  <template #icon><ReloadOutlined /></template>
                  重置
                </a-button>
                <a-button @click="handleRefresh">
                  <template #icon><SyncOutlined /></template>
                  刷新
                </a-button>
                <a-button :loading="exportLoading" @click="handleExport">
                  <template #icon><DownloadOutlined /></template>
                  导出CSV
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="graph-card">
      <template #extra>
        <a-space>
          <a-button size="small" @click="zoomIn">
            <template #icon><ZoomInOutlined /></template>
            放大
          </a-button>
          <a-button size="small" @click="zoomOut">
            <template #icon><ZoomOutOutlined /></template>
            缩小
          </a-button>
          <a-button size="small" @click="fitView">
            <template #icon><FullscreenOutlined /></template>
            自适应
          </a-button>
        </a-space>
      </template>
      <div v-if="!hasSearched" class="topology-empty-state">
        <a-empty description="请先选择模型/起点CI并点击搜索以展示拓扑图" />
      </div>
      <div v-else-if="!nodes.length" class="topology-empty-state">
        <a-empty description="未查询到符合条件的拓扑关系" />
      </div>
      <div v-else ref="graphContainer" class="graph-container"></div>
    </a-card>

    <CiDetailDrawer
      v-model:visible="detailDrawerVisible"
      :instance-id="currentInstanceId"
      @deleted="handleNodeDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed, createApp, h } from 'vue'
import { message } from 'ant-design-vue'
import {
  SearchOutlined,
  ReloadOutlined,
  SyncOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  DownloadOutlined
} from '@ant-design/icons-vue'
import { Graph } from '@antv/g6'
import { getTopology, exportTopology } from '@/api/cmdb-relation'
import { getModels } from '@/api/cmdb'
import { getInstances } from '@/api/ci'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'
import { getModelIconAssetUrl, getModelIconComponent } from '@/utils/cmdbModelIcons'
import {
  buildNodeToggleBadges,
  buildVisibleTopology,
  resolveNodeToggleAction
} from './utils/topologyVisibility'

const TOPOLOGY_DEPTH_LIMIT = Math.max(1, Number((import.meta as any)?.env?.VITE_TOPOLOGY_DEPTH_LIMIT || 10) || 10)

const loading = ref(false)
const exportLoading = ref(false)
const searchKeyword = ref('')
const searchModelIds = ref<number[]>([])
const searchCiIds = ref<number[]>([])
const relationDepth = ref(1)
const layout = ref('dagre')
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const hasSearched = ref(false)
const selectedNodeId = ref<string | null>(null)
const collapsedNodeIds = ref<Set<string>>(new Set())
const models = ref<any[]>([])
const candidateCis = ref<any[]>([])
const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)
const graphContainer = ref<HTMLElement>()
let graph: any = null

const modelColorMap: Record<number, string> = {}

const modelMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  models.value.forEach((model) => {
    map[model.id] = model
  })
  return map
})

const getModelKeyFields = (modelId?: number) => {
  if (!modelId) return []
  const model = modelMap.value[modelId]
  const codes = model?.key_field_codes
  return Array.isArray(codes) ? codes.slice(0, 3) : []
}

const formatDisplayValue = (value: any): string => {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.filter(Boolean).join(',')
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return ''
    }
  }
  return String(value).trim()
}

const getNodeKeyValues = (node: any): string[] => {
  if (Array.isArray(node?.display_subtitles) && node.display_subtitles.length > 0) {
    return node.display_subtitles.map((value: any) => formatDisplayValue(value)).filter(Boolean)
  }
  const attrs = node?.attributes || {}
  const keyFieldCodes = getModelKeyFields(node?.model_id)
  return keyFieldCodes.map((code) => formatDisplayValue(attrs?.[code])).filter(Boolean)
}

const getNodePrimaryText = (node: any): string => {
  const keyValues = getNodeKeyValues(node)
  if (keyValues.length > 0) return keyValues.join(' | ')
  return '未配置关键属性'
}

const getCiDisplayText = (ci: any): string => {
  const keyFieldCodes = getModelKeyFields(ci?.model_id)
  const values = keyFieldCodes.map((code) => formatDisplayValue(ci?.attributes?.[code])).filter(Boolean)
  if (values.length > 0) return values.join(' | ')
  return '未配置关键属性'
}

const filteredCandidateCis = computed(() => {
  const list = candidateCis.value || []
  if (!searchModelIds.value.length) return list
  const modelIdSet = new Set(searchModelIds.value)
  return list.filter((ci) => modelIdSet.has(ci.model_id))
})

const getNodeIconComponent = (node: any) => {
  const modelIcon = modelMap.value[node?.model_id]?.icon || node?.model_icon
  return getModelIconComponent(modelIcon)
}

const getNodeIconUrl = (node: any) => {
  return modelMap.value[node?.model_id]?.icon_url || node?.model_icon_url || ''
}

const getThemeColor = (name: string, fallback: string) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const getNodeColor = (node: any) => {
  if (modelColorMap[node.model_id]) {
    return modelColorMap[node.model_id]
  }
  const colors = [
    getThemeColor('--app-accent', '#1677ff'),
    getThemeColor('--arco-success', '#52c41a'),
    getThemeColor('--arco-warning', '#faad14'),
    getThemeColor('--arco-danger', '#f5222d'),
    '#722ed1',
    '#13c2c2',
    '#eb2f96',
    '#fa8c16'
  ]
  const color = colors[node.model_id % colors.length]
  modelColorMap[node.model_id] = color
  return color
}

const builtinIconDataUrlCache: Record<string, string> = {}
const iconUrlStatus = ref<Record<string, 'ok' | 'fail'>>({})

const getAntdIconSvgMarkup = (iconName?: string) => {
  const iconComponent = getModelIconComponent(iconName)
  const container = document.createElement('div')
  const app = createApp({
    render() {
      return h(iconComponent, {
        style: {
          fontSize: '24px',
          color: getThemeColor('--app-accent', '#1677ff')
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
  svg.style.color = getThemeColor('--app-accent', '#1677ff')
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
  const assetUrl = getModelIconAssetUrl(cacheKey)
  if (assetUrl) {
    builtinIconDataUrlCache[cacheKey] = assetUrl
    return assetUrl
  }
  const svg = getAntdIconSvgMarkup(cacheKey)
  const dataUrl = svg
    ? toSvgBase64DataUrl(svg)
    : ''
  builtinIconDataUrlCache[cacheKey] = dataUrl
  return dataUrl
}

const markIconUrlFailed = (url?: string) => {
  if (!url) return
  iconUrlStatus.value = { ...iconUrlStatus.value, [url]: 'fail' }
}

const ensureIconUrlStatus = (url?: string) => {
  if (!url) return
  if (iconUrlStatus.value[url]) return
  const img = new Image()
  img.onload = () => {
    iconUrlStatus.value = { ...iconUrlStatus.value, [url]: 'ok' }
  }
  img.onerror = () => {
    iconUrlStatus.value = { ...iconUrlStatus.value, [url]: 'fail' }
    nextTick(() => renderGraph())
  }
  img.src = url
}

const getGraphNodeIconSrc = (node: any) => {
  const iconUrl = getNodeIconUrl(node)
  if (iconUrl) {
    ensureIconUrlStatus(iconUrl)
    if (iconUrlStatus.value[iconUrl] === 'ok') {
      return iconUrl
    }
  }
  const modelIcon = modelMap.value[node?.model_id]?.icon || node?.model_icon
  return getBuiltinIconDataUrl(modelIcon)
}

const applyGraphData = (data: { nodes: any[]; edges: any[] }) => {
  if (!graph) return
  if (typeof graph.changeData === 'function') {
    graph.changeData(data)
    return
  }
  if (typeof graph.setData === 'function') {
    graph.setData(data)
    if (typeof graph.render === 'function') {
      graph.render()
    } else if (typeof graph.draw === 'function') {
      graph.draw()
    }
    return
  }
  console.warn('Graph data update API not found')
}

const initGraph = () => {
  if (!graphContainer.value) return

  if (graph) {
    graph.destroy?.()
    graph = null
  }

  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: graphContainer.value.clientHeight - 24,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    defaultNode: {
      type: 'circle',
      size: 52,
      style: {
        lineWidth: 2,
        stroke: '#bcd8ff',
        fill: '#ffffff'
      },
    },
    defaultEdge: {
      type: 'cubic-horizontal',
      style: {
        stroke: '#3b82f6',
        lineWidth: 2,
        endArrow: true,
        opacity: 0.9
      }
    },
    animation: true,
    layout: {
      type: layout.value,
      preventOverlap: true,
      rankdir: 'LR',
      nodesep: 60,
      ranksep: 140,
      nodeSize: 72,
      animation: true,
      animationDuration: 320
    }
  } as any)

  graph.on('node:click', (evt: any) => {
    const node = evt?.item || evt?.target
    if (node) {
      const model = typeof node.getModel === 'function' ? node.getModel() : node
      const nodeId = String(model?.id || '')
      const rawNodeId = String(model?.ci_id ?? nodeId.replace(/^ci-/, ''))
      const action = resolveNodeToggleAction(evt)
      if (action && rawNodeId) {
        if (action === 'expand') {
          if (collapsedNodeIds.value.has(rawNodeId)) {
            collapsedNodeIds.value.delete(rawNodeId)
            collapsedNodeIds.value = new Set(collapsedNodeIds.value)
            void renderGraph()
          }
          return
        }
        const visibility = buildVisibleTopology(nodes.value, edges.value, collapsedNodeIds.value)
        if (visibility.collapsibleNodeIds.has(rawNodeId)) {
          collapsedNodeIds.value.add(rawNodeId)
          collapsedNodeIds.value = new Set(collapsedNodeIds.value)
          void renderGraph()
        }
        return
      }
      selectedNodeId.value = nodeId || null
      void renderGraph()
    }
  })

  graph.on('node:dblclick', (evt: any) => {
    const node = evt?.item || evt?.target
    if (!node) return
    const model = typeof node.getModel === 'function' ? node.getModel() : node
    const ciId = Number(model?.ci_id ?? String(model?.id || '').replace(/^ci-/, ''))
    currentInstanceId.value = Number.isNaN(ciId) ? null : ciId
    detailDrawerVisible.value = true
  })

  graph.on('canvas:click', () => {
    selectedNodeId.value = null
    void renderGraph()
  })

  renderGraph({ fit: true })
}

const applyTopologyFocusState = async (focusNodeId: string | null) => {
  if (!graph || typeof graph.setItemState !== 'function' || typeof graph.findById !== 'function') return
  try {
    const nodeIds = nodes.value.map((node) => `ci-${String(node.id)}`)
    const edgeIds = edges.value.map((edge, index) => `rel-${String(edge.id || index)}`)

    nodeIds.forEach((id) => {
      const item = graph.findById(id)
      if (!item) return
      graph.setItemState(item, 'active', false)
      graph.setItemState(item, 'inactive', false)
    })
    edgeIds.forEach((id) => {
      const item = graph.findById(id)
      if (!item) return
      graph.setItemState(item, 'active', false)
      graph.setItemState(item, 'inactive', false)
    })
    if (!focusNodeId) return

    const activeNodeIds = new Set<string>([focusNodeId])
    const activeEdgeIds = new Set<string>()
    edges.value.forEach((edge, index) => {
      const edgeId = `rel-${String(edge.id || index)}`
      const sourceId = `ci-${String(edge.source)}`
      const targetId = `ci-${String(edge.target)}`
      if (sourceId === focusNodeId || targetId === focusNodeId) {
        activeEdgeIds.add(edgeId)
        activeNodeIds.add(sourceId)
        activeNodeIds.add(targetId)
      }
    })

    nodeIds.forEach((id) => {
      const item = graph.findById(id)
      if (!item) return
      graph.setItemState(item, activeNodeIds.has(id) ? 'active' : 'inactive', true)
    })
    edgeIds.forEach((id) => {
      const item = graph.findById(id)
      if (!item) return
      graph.setItemState(item, activeEdgeIds.has(id) ? 'active' : 'inactive', true)
    })
  } catch (error) {
    console.warn('applyTopologyFocusState failed', error)
  }
}

const renderGraph = async ({ fit = false }: { fit?: boolean } = {}) => {
  if (!graph) return
  const visibility = buildVisibleTopology(nodes.value, edges.value, collapsedNodeIds.value)
  const visibleNodes = visibility.nodes
  const visibleEdges = visibility.edges
  const collapsibleNodeIds = visibility.collapsibleNodeIds
  const visibleNodeIdSet = new Set(visibleNodes.map((node) => `ci-${String(node.id)}`))
  const focusedNodeId = visibleNodeIdSet.has(selectedNodeId.value || '') ? selectedNodeId.value : null
  if (selectedNodeId.value && !focusedNodeId) {
    selectedNodeId.value = null
  }
  const activeNodeIdSet = new Set<string>()
  const activeEdgeIdSet = new Set<string>()
  if (focusedNodeId) {
    activeNodeIdSet.add(focusedNodeId)
    visibleEdges.forEach((edge, index) => {
      const edgeId = `rel-${String(edge.id || index)}`
      const sourceId = `ci-${String(edge.source)}`
      const targetId = `ci-${String(edge.target)}`
      if (sourceId === focusedNodeId || targetId === focusedNodeId) {
        activeEdgeIdSet.add(edgeId)
        activeNodeIdSet.add(sourceId)
        activeNodeIdSet.add(targetId)
      }
    })
  }

  const graphNodes = visibleNodes.map((node) => ({
    id: `ci-${String(node.id)}`,
    ci_id: Number(node.id),
    model_id: node.model_id,
    type: 'circle',
    draggable: true,
    style: {
      opacity: focusedNodeId && !activeNodeIdSet.has(`ci-${String(node.id)}`) ? 0.2 : 1,
      size: 58,
      fill: '#ffffff',
      stroke: node.has_open_alert ? '#ef4444' : (focusedNodeId && activeNodeIdSet.has(`ci-${String(node.id)}`) ? '#2563eb' : '#bcd8ff'),
      lineWidth: node.has_open_alert ? 2.6 : (focusedNodeId && activeNodeIdSet.has(`ci-${String(node.id)}`) ? 2.4 : 1.8),
      icon: true,
      iconSrc: getGraphNodeIconSrc(node),
      iconWidth: 22,
      iconHeight: 22,
      badges: buildNodeToggleBadges(String(node.id), collapsedNodeIds.value, collapsibleNodeIds),
      labelText: getNodePrimaryText(node),
      labelPlacement: 'bottom',
      labelFill: getThemeColor('--app-text-primary', '#1f1f1f'),
      labelFontSize: 12,
      shadowColor: node.has_open_alert ? 'rgba(239, 68, 68, 0.42)' : 'rgba(59, 130, 246, 0.24)',
      shadowBlur: node.has_open_alert ? 20 : (focusedNodeId && activeNodeIdSet.has(`ci-${String(node.id)}`) ? 18 : 14),
    },
    label: getNodePrimaryText(node)
  }))

  const graphEdges = visibleEdges.map((edge, index) => ({
    id: `rel-${String(edge.id || index)}`,
    source: `ci-${String(edge.source)}`,
    target: `ci-${String(edge.target)}`,
    style: {
      endArrow: edge.direction === 'directed' ? true : false,
      labelText: edge.relation_type_name || '',
      stroke: focusedNodeId && activeEdgeIdSet.has(`rel-${String(edge.id || index)}`) ? '#1d4ed8' : '#3b82f6',
      lineWidth: focusedNodeId && activeEdgeIdSet.has(`rel-${String(edge.id || index)}`) ? 3.4 : 2,
      opacity: focusedNodeId ? (activeEdgeIdSet.has(`rel-${String(edge.id || index)}`) ? 1 : 0.12) : 0.88
    },
    label: edge.relation_type_name || ''
  }))

  applyGraphData({
    nodes: graphNodes,
    edges: graphEdges
  })

  if (fit && typeof graph.fitView === 'function') {
    graph.fitView()
  }
}

const validateDepthLimit = () => {
  const depth = Number(relationDepth.value || 1)
  if (depth <= TOPOLOGY_DEPTH_LIMIT) return true
  message.warning(`当前深度为 ${depth}，已超出上限 ${TOPOLOGY_DEPTH_LIMIT}，请调整后再操作`)
  return false
}

const fetchTopology = async () => {
  loading.value = true
  try {
    const res = await getTopology({
      model_ids: searchModelIds.value.join(','),
      ci_ids: searchCiIds.value.join(','),
      depth: relationDepth.value,
      keyword: searchKeyword.value
    })
    if (res.code === 200) {
      nodes.value = res.data.nodes || []
      edges.value = (res.data.edges || []).map((edge: any) => ({
        ...edge,
        source_name: nodes.value.find(n => n.id === edge.source)?.name || edge.source,
        target_name: nodes.value.find(n => n.id === edge.target)?.name || edge.target
      }))
      collapsedNodeIds.value = new Set()
      await nextTick()
      if (!graph && graphContainer.value) {
        initGraph()
      } else {
        await renderGraph({ fit: true })
      }
    }
  } catch (error: any) {
    console.error(error)
    message.error(error?.response?.data?.message || '拓扑查询失败')
  } finally {
    loading.value = false
  }
}

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      models.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchCandidateCis = async () => {
  try {
    const res = await getInstances({ per_page: 1000 })
    if (res.code === 200) {
      candidateCis.value = res.data.items || []
    }
  } catch (error) {
    console.error(error)
  }
}



const handleNodeDeleted = () => {
  detailDrawerVisible.value = false
  if (hasSearched.value) {
    void fetchTopology()
  }
}

const handleSearch = () => {
  if (!validateDepthLimit()) return
  hasSearched.value = true
  selectedNodeId.value = null
  void nextTick(async () => {
    if (!graph && graphContainer.value) {
      initGraph()
    }
    await fetchTopology()
  })
}

const handleReset = () => {
  searchKeyword.value = ''
  searchModelIds.value = []
  searchCiIds.value = []
  relationDepth.value = 1
  hasSearched.value = false
  selectedNodeId.value = null
  collapsedNodeIds.value = new Set()
  nodes.value = []
  edges.value = []
  if (graph) {
    graph.destroy?.()
    graph = null
  }
}

const handleRefresh = () => {
  if (!hasSearched.value) return
  if (!validateDepthLimit()) return
  void fetchTopology()
}

const handleExport = async () => {
  if (!hasSearched.value) {
    message.warning('请先搜索拓扑后再导出')
    return
  }
  if (!validateDepthLimit()) return
  exportLoading.value = true
  try {
    const exported = await exportTopology({
      format: 'csv',
      model_ids: searchModelIds.value.join(','),
      ci_ids: searchCiIds.value.join(','),
      depth: relationDepth.value,
      keyword: searchKeyword.value
    }) as unknown

    const blob = exported instanceof Blob
      ? exported
      : new Blob([exported as BlobPart], { type: 'text/csv;charset=utf-8;' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `topology_${Date.now()}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (error: any) {
    message.error(error.response?.data?.message || '导出失败')
  } finally {
    exportLoading.value = false
  }
}

const zoomIn = () => {
  if (graph) {
    const currentZoom = typeof graph.getZoom === 'function' ? graph.getZoom() : 1
    if (typeof graph.zoomTo === 'function') {
      graph.zoomTo(currentZoom * 1.2)
    } else if (typeof graph.zoomBy === 'function') {
      graph.zoomBy(1.2)
    }
  }
}

const zoomOut = () => {
  if (graph) {
    const currentZoom = typeof graph.getZoom === 'function' ? graph.getZoom() : 1
    if (typeof graph.zoomTo === 'function') {
      graph.zoomTo(currentZoom * 0.8)
    } else if (typeof graph.zoomBy === 'function') {
      graph.zoomBy(0.8)
    }
  }
}

const fitView = () => {
  if (graph) {
    if (typeof graph.fitView === 'function') {
      graph.fitView()
    } else if (typeof graph.fitCenter === 'function') {
      graph.fitCenter()
    }
  }
}

const handleResize = () => {
  if (graph && graphContainer.value) {
    const width = graphContainer.value.clientWidth
    const height = graphContainer.value.clientHeight - 24
    if (typeof graph.changeSize === 'function') {
      graph.changeSize(width, height)
    } else if (typeof graph.setSize === 'function') {
      graph.setSize(width, height)
    }
  }
}

watch(layout, () => {
  if (graph) {
    const layoutOptions = layout.value === 'dagre'
      ? {
          type: 'dagre',
          rankdir: 'LR',
          nodesep: 60,
          ranksep: 140,
          nodeSize: 72,
          animation: true,
          animationDuration: 320
        }
      : {
          type: layout.value,
          preventOverlap: true,
          nodeSpacing: 80,
          linkDistance: 130,
          animation: true,
          animationDuration: 320
        }
    if (typeof graph.updateLayout === 'function') {
      graph.updateLayout(layoutOptions)
    } else if (typeof graph.setLayout === 'function') {
      graph.setLayout(layoutOptions)
      if (typeof graph.render === 'function') {
        void graph.render()
      }
    }
  }
})

watch(searchModelIds, () => {
  if (!searchCiIds.value.length) return
  const existsSet = new Set(filteredCandidateCis.value.map((ci) => ci.id))
  searchCiIds.value = searchCiIds.value.filter((ciId) => existsSet.has(ciId))
})

onMounted(() => {
  void fetchModels()
  void fetchCandidateCis()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (graph) {
    graph.destroy()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.topology-page {
  padding: 16px;
  height: calc(100vh - 24px);
  display: flex;
  flex-direction: column;
}

.search-card {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.search-form {
  width: 100%;
}

.search-form :deep(.ant-form-item) {
  margin-bottom: 0;
  width: 100%;
}

.topology-filter-row {
  width: 100%;
}

.topology-action-row {
  width: 100%;
  margin-top: 8px;
}

.search-buttons {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

@media (max-width: 992px) {
  .search-buttons {
    justify-content: flex-start;
  }
}

.graph-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.graph-container {
  flex: 1;
  min-height: 400px;
}

.topology-empty-state {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
