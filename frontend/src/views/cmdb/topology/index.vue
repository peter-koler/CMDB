<template>
  <div class="topology-page">
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
                v-model:value="searchModelId"
                placeholder="请选择模型"
                style="width: 100%"
                allowClear
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
                v-model:value="searchCiId"
                placeholder="按关键属性选择起点"
                style="width: 100%"
                allowClear
                show-search
                option-filter-prop="label"
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
              <a-select v-model:value="relationDepth" style="width: 100%">
                <a-select-option :value="1">1层</a-select-option>
                <a-select-option :value="2">2层</a-select-option>
                <a-select-option :value="3">3层</a-select-option>
                <a-select-option :value="4">4层</a-select-option>
              </a-select>
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
      <div ref="graphContainer" class="graph-container"></div>
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
  ApiOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  ContainerOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  SearchOutlined,
  ReloadOutlined,
  SyncOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  DownloadOutlined,
  GlobalOutlined,
  HddOutlined,
  LaptopOutlined
} from '@ant-design/icons-vue'
import { Graph } from '@antv/g6'
import { getTopology, exportTopology } from '@/api/cmdb-relation'
import { getModels } from '@/api/cmdb'
import { getInstances } from '@/api/ci'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'

const loading = ref(false)
const exportLoading = ref(false)
const searchKeyword = ref('')
const searchModelId = ref<number | null>(null)
const searchCiId = ref<number | null>(null)
const relationDepth = ref(1)
const layout = ref('force')
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const models = ref<any[]>([])
const candidateCis = ref<any[]>([])
const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)
const graphContainer = ref<HTMLElement>()
let graph: any = null

const modelColorMap: Record<number, string> = {}
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
  if (!searchModelId.value) return list
  return list.filter((ci) => ci.model_id === searchModelId.value)
})

const getNodeIconComponent = (node: any) => {
  const modelIcon = modelMap.value[node?.model_id]?.icon || node?.model_icon
  return iconComponentMap[modelIcon] || AppstoreOutlined
}

const getNodeIconUrl = (node: any) => {
  return modelMap.value[node?.model_id]?.icon_url || node?.model_icon_url || ''
}

const getNodeColor = (node: any) => {
  if (modelColorMap[node.model_id]) {
    return modelColorMap[node.model_id]
  }
  const colors = [
    '#1890ff',
    '#52c41a',
    '#faad14',
    '#f5222d',
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

  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: graphContainer.value.clientHeight - 24,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    defaultNode: {
      size: 40,
      style: {
        lineWidth: 2,
        stroke: '#fff'
      },
      labelCfg: {
        style: {
          fill: '#000',
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
      type: layout.value,
      preventOverlap: true,
      nodeSpacing: 100,
      linkDistance: 150
    }
  } as any)

  graph.on('node:click', (evt: any) => {
    const node = evt?.item || evt?.target
    if (node) {
      const model = typeof node.getModel === 'function' ? node.getModel() : node
      currentInstanceId.value = Number(model?.id)
      detailDrawerVisible.value = true
    }
  })

  renderGraph()
}

const renderGraph = () => {
  if (!graph) return

  const graphNodes = nodes.value.map((node) => ({
    id: String(node.id),
    model_id: node.model_id,
    type: 'image',
    draggable: true,
    style: {
      img: getGraphNodeIconSrc(node),
      src: getGraphNodeIconSrc(node),
      size: 36,
      lineWidth: 0,
      labelText: getNodePrimaryText(node),
      labelPlacement: 'bottom',
      labelFill: '#1f1f1f',
      labelFontSize: 12
    },
    label: getNodePrimaryText(node)
  }))

  const graphEdges = edges.value.map((edge, index) => ({
    id: String(edge.id || index),
    source: String(edge.source),
    target: String(edge.target),
    style: {
      endArrow: edge.direction === 'directed' ? true : false,
      labelText: edge.relation_type_name || ''
    },
    label: edge.relation_type_name || ''
  }))

  applyGraphData({
    nodes: graphNodes,
    edges: graphEdges
  })
}

const fetchTopology = async () => {
  loading.value = true
  try {
    const res = await getTopology({
      model_id: searchModelId.value,
      ci_id: searchCiId.value,
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
      nextTick(() => {
        renderGraph()
      })
    }
  } catch (error) {
    console.error(error)
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
  fetchTopology()
}

const handleSearch = () => {
  fetchTopology()
}

const handleReset = () => {
  searchKeyword.value = ''
  searchModelId.value = null
  searchCiId.value = null
  relationDepth.value = 1
  fetchTopology()
}

const handleRefresh = () => {
  fetchTopology()
}

const handleExport = async () => {
  exportLoading.value = true
  try {
    const data = await exportTopology({
      format: 'csv',
      model_id: searchModelId.value,
      ci_id: searchCiId.value,
      depth: relationDepth.value,
      keyword: searchKeyword.value
    })

    const blob = data instanceof Blob ? data : new Blob([data], { type: 'text/csv;charset=utf-8;' })
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
    const layoutOptions = {
      type: layout.value,
      preventOverlap: true,
      nodeSpacing: 100,
      linkDistance: 150
    }
    if (typeof graph.updateLayout === 'function') {
      graph.updateLayout(layoutOptions)
    } else if (typeof graph.setLayout === 'function') {
      graph.setLayout(layoutOptions)
      if (typeof graph.render === 'function') {
        graph.render()
      }
    }
  }
})

watch(searchModelId, () => {
  if (!searchCiId.value) return
  const exists = filteredCandidateCis.value.some((ci) => ci.id === searchCiId.value)
  if (!exists) {
    searchCiId.value = null
  }
})

onMounted(() => {
  fetchModels()
  fetchCandidateCis()
  nextTick(() => {
    initGraph()
    fetchTopology()
  })
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
</style>
