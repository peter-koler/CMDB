<template>
  <div class="app-page topology-render-page">
    <a-card :bordered="false" class="main-card">
      <template #title>
        <span class="page-title">拓扑动态视图</span>
      </template>
      <template #extra>
        <a-space>
          <a-select
            v-model:value="selectedTemplateId"
            style="width: 240px"
            :options="templateOptions"
            placeholder="请选择拓扑模板"
            allow-clear
          />
          <a-button @click="goTemplateList">模板中心</a-button>
          <a-button type="primary" @click="goTemplateEdit" :disabled="!selectedTemplateId">配置当前模板</a-button>
        </a-space>
      </template>

      <a-row :gutter="16">
        <a-col :xs="24" :xl="18">
          <div class="graph-wrapper">
            <div class="graph-toolbar">
              <a-space>
                <a-button-group size="small">
                  <a-button @click="expandAll">全部展开</a-button>
                  <a-button @click="collapseToSeed">重置路径</a-button>
                </a-button-group>
                <a-divider type="vertical" />
                <a-button size="small" @click="handleFitView">视角居中</a-button>
                <a-tag color="blue">{{ currentTemplate?.layoutDirection === 'vertical' ? '纵向分层' : '横向分层' }}</a-tag>
                <span class="graph-stats" v-if="stats.nodeCount">
                  节点: <b>{{ stats.nodeCount }}</b> | 关系: <b>{{ stats.edgeCount }}</b>
                </span>
              </a-space>
              <div v-if="loading" class="loading-tag">
                <a-spin size="small" /> 视图构建中...
              </div>
            </div>
            <div v-if="layerPreview.length > 0" class="layer-preview">
              <div v-for="item in layerPreview" :key="item.id" class="layer-chip">
                <div class="layer-chip-name">{{ item.name }}</div>
                <div class="layer-chip-models">{{ item.models }}</div>
                <div class="layer-chip-count">节点 {{ item.count }}</div>
              </div>
            </div>
            <div class="graph-stage">
              <div
                v-if="layerBands.length > 0"
                class="layer-overlay"
                :class="currentTemplate?.layoutDirection === 'vertical' ? 'overlay-vertical' : 'overlay-horizontal'"
                :style="overlayGridStyle"
              >
                <div v-for="band in layerBands" :key="band.id" class="layer-band">
                  <div class="layer-band-title">{{ band.name }}</div>
                </div>
              </div>
              <div ref="graphContainer" class="graph-container"></div>
            </div>
          </div>
        </a-col>

        <a-col :xs="24" :xl="6">
          <a-space direction="vertical" style="width: 100%" size="middle">
            <a-card size="small" title="视图规则摘要" class="info-card">
              <a-empty v-if="!currentTemplate" description="请选择上方模板" />
              <a-descriptions v-else :column="1" size="small">
                <a-descriptions-item label="名称">{{ currentTemplate.name }}</a-descriptions-item>
                <a-descriptions-item label="分组依据">{{ currentTemplate.groupBy || '未设置' }}</a-descriptions-item>
                <a-descriptions-item label="聚合策略">{{ currentTemplate.aggregateEnabled ? '已开启' : '平铺展示' }}</a-descriptions-item>
              </a-descriptions>
            </a-card>

            <a-card size="small" title="节点属性详情" class="info-card">
              <a-empty v-if="!activeNode" description="点击图中节点查看详情" />
              <div v-else class="detail-content">
                <div class="ci-header">
                  <div class="ci-icon" :style="{ backgroundColor: getModelStyle(activeNode.modelKey).color }">
                    {{ activeNode.modelKey.charAt(0).toUpperCase() }}
                  </div>
                  <div class="ci-title">
                    <div class="ci-name">{{ activeNode.name }}</div>
                    <div class="ci-type">{{ getModelLabel(activeNode.modelKey) }}</div>
                  </div>
                </div>
                <div style="margin-top: 10px" v-if="activeNode.nodeKind !== 'aggregate'">
                  <a-button type="primary" ghost size="small" @click="openCiDetail">查看CI详情</a-button>
                </div>
                <a-divider style="margin: 12px 0" />
                <a-descriptions :column="1" size="small" layout="horizontal">
                  <a-descriptions-item label="实时状态">
                    <a-tag :color="statusMap[activeNode.status]?.tag">{{ activeNode.status }}</a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item v-if="activeNode.idc" label="物理机房">{{ activeNode.idc }}</a-descriptions-item>
                  <a-descriptions-item v-if="activeNode.subnet" label="所属网段">{{ activeNode.subnet }}</a-descriptions-item>
                  <a-descriptions-item v-if="activeNode.owner" label="责任人">{{ activeNode.owner }}</a-descriptions-item>
                </a-descriptions>
              </div>
            </a-card>
          </a-space>
        </a-col>
      </a-row>
    </a-card>
    <CiDetailDrawer
      v-model:visible="detailDrawerVisible"
      :instance-id="currentInstanceId"
      @deleted="handleNodeDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, createApp, h, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Graph } from '@antv/g6'
import { useRoute, useRouter } from 'vue-router'
import {
  buildRenderedGraphData,
  extractByTemplate,
  RenderNode
} from './utils/topology-template-runtime'
import { listCmdbTopologyTemplates, TopologyTemplate as ApiTopologyTemplate } from '@/api/cmdb-topology-template'
import { getTopology, getRelationTypes } from '@/api/cmdb-relation'
import { getModels } from '@/api/cmdb'
import { message } from 'ant-design-vue'
import { getModelIconAssetUrl, getModelIconComponent } from '@/utils/cmdbModelIcons'
import { buildNodeToggleBadges, resolveNodeToggleAction } from '../topology/utils/topologyVisibility'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'

const route = useRoute()
const router = useRouter()
const graphContainer = ref<HTMLElement>()
const loading = ref(false)

// --- 状态数据 ---
const templates = ref<ApiTopologyTemplate[]>([])
const selectedTemplateId = ref('')
const activeNode = ref<RenderNode | null>(null)
const activeNodeId = ref('')
const collapsedNodeIds = ref<Set<string>>(new Set())
const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)
const topologyNodes = ref<any[]>([])
const topologyEdges = ref<any[]>([])
const cmdbModels = ref<any[]>([])
const relationTypes = ref<any[]>([])
let graph: Graph | null = null

// --- 视觉规范 ---
const statusMap: Record<string, any> = {
  ALARM: { tag: 'error', color: '#ff4d4f' },
  WARN: { tag: 'warning', color: '#faad14' },
  RUNNING: { tag: 'success', color: '#52c41a' },
  OFFLINE: { tag: 'default', color: '#bfbfbf' }
}

const getModelStyle = (key: string) => {
  const styles: Record<string, string> = {
    domain: '#1677ff', application: '#52c41a', cloud_server: '#722ed1', database: '#fa8c16', aggregate: '#8c8c8c'
  }
  return { color: styles[key] || '#1677ff' }
}

// --- 计算逻辑 ---
const templateOptions = computed(() => templates.value.map(t => ({ label: t.name, value: t.id })))
const currentTemplate = computed<ApiTopologyTemplate | undefined>(() => {
  const found = templates.value.find(t => t.id === selectedTemplateId.value)
  if (!found) return undefined
  return found
})
const modelById = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  cmdbModels.value.forEach((item: any) => {
    const id = Number(item?.id || 0)
    if (id > 0) map[id] = item
  })
  return map
})
const relationTypeById = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  relationTypes.value.forEach((item: any) => {
    const id = Number(item?.id || 0)
    if (id > 0) map[id] = item
  })
  return map
})
const renderedData = computed(() => {
  if (!currentTemplate.value) return { nodes: [], edges: [], combos: [] }
  return buildRenderedGraphData(
    currentTemplate.value,
    topologyNodes.value,
    topologyEdges.value,
    { modelById: modelById.value, relationTypeById: relationTypeById.value },
    collapsedNodeIds.value
  )
})
const fullExtractedData = computed(() => {
  if (!currentTemplate.value) return { nodes: [], edges: [], seedNodeIds: [] as string[] }
  return extractByTemplate(
    currentTemplate.value,
    topologyNodes.value,
    topologyEdges.value,
    { modelById: modelById.value, relationTypeById: relationTypeById.value },
    new Set()
  )
})
const stats = computed(() => ({
  nodeCount: renderedData.value.nodes?.length || 0,
  edgeCount: renderedData.value.edges?.length || 0
}))
const getModelLabel = (key: string) => {
  if (key === 'aggregate') return '聚合池'
  const found = cmdbModels.value.find((item: any) => String(item?.code || '') === key)
  return String(found?.name || key)
}

const getThemeColor = (name: string, fallback: string) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const toSvgBase64DataUrl = (svg: string) => {
  const utf8 = unescape(encodeURIComponent(svg))
  const base64 = window.btoa(utf8)
  return `data:image/svg+xml;base64,${base64}`
}

const getAntdIconDataUrl = (iconName?: string) => {
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
  const result = toSvgBase64DataUrl(svg.outerHTML)
  app.unmount()
  return result
}

const getNodeIconSrc = (node: any) => {
  if (node?.modelIconUrl) return String(node.modelIconUrl)
  const iconKey = String(node?.modelIcon || modelById.value[Number(node?.modelId || 0)]?.icon || 'AppstoreOutlined')
  const asset = getModelIconAssetUrl(iconKey)
  if (asset) return asset
  return getAntdIconDataUrl(iconKey)
}

const layerPreview = computed(() => {
  if (!currentTemplate.value) return []
  const layers = currentTemplate.value.layers || []
  return layers.map((layer) => {
    const count = renderedData.value.nodes.filter((node: any) => layer.modelKeys.includes(node.modelKey)).length
    return {
      id: layer.id,
      name: layer.name || '未命名层',
      models: layer.modelKeys.map((key) => getModelLabel(key)).join(' / ') || '未配置模型',
      count
    }
  })
})

const layerBands = computed(() => {
  return layerPreview.value
})

const overlayGridStyle = computed(() => {
  const count = Math.max(layerBands.value.length, 1)
  if (currentTemplate.value?.layoutDirection === 'vertical') {
    return { gridTemplateRows: `repeat(${count}, 1fr)` }
  }
  return { gridTemplateColumns: `repeat(${count}, 1fr)` }
})

// --- G6 v5 专业级渲染器 ---
const initGraph = () => {
  if (!graphContainer.value || graph) return

  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: graphContainer.value.clientHeight,
    autoResize: true,
    data: { nodes: [], edges: [] },
    node: {
      style: {
        size: 56,
        type: 'circle',
        fill: '#ffffff',
        stroke: (d: any) => d.status === 'ALARM' ? '#ef4444' : '#bcd8ff',
        lineWidth: (d: any) => d.status === 'ALARM' ? 2.6 : 1.8,
        icon: true,
        iconWidth: 22,
        iconHeight: 22,
        labelFill: '#1f1f1f',
        labelFontSize: 12,
        labelPlacement: 'bottom',
        shadowColor: 'rgba(59,130,246,0.24)',
        shadowBlur: 12,
        cursor: 'pointer',
      },
      state: {
        selected: { stroke: '#1677ff', lineWidth: 2.8, fill: '#ffffff' },
        hover: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.1)' }
      }
    },
    // 连线样式
    edge: {
      style: {
        endArrow: true,
        stroke: '#d9d9d9',
        lineWidth: 1,
        router: 'orth', // 直角连线更符合 IT 拓扑感
        labelText: (d: any) => d.type,
        labelFontSize: 10,
        labelFill: '#bfbfbf',
        labelBackground: true,
        labelBackgroundFill: '#fff',
      }
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element', 'click-select', 'hover-activate'],
  })

  graph.on('node:click', (evt: any) => {
    const nodeId = String(evt?.target?.id || evt?.item?.id || '')
    if (!nodeId) return
    const action = resolveNodeToggleAction(evt)
    if (action) {
      if (action === 'expand') {
        collapsedNodeIds.value.delete(nodeId)
        collapsedNodeIds.value = new Set(collapsedNodeIds.value)
      } else {
        const hasChildrenInFullGraph = fullExtractedData.value.edges.some((edge: any) => edge.source === nodeId)
        if (hasChildrenInFullGraph) {
          collapsedNodeIds.value.add(nodeId)
          collapsedNodeIds.value = new Set(collapsedNodeIds.value)
        }
      }
      return
    }

    activeNodeId.value = nodeId
    activeNode.value = renderedData.value.nodes.find((n: any) => n.id === nodeId) || null

    const isCollapsed = collapsedNodeIds.value.has(nodeId)
    if (isCollapsed) {
      collapsedNodeIds.value.delete(nodeId)
      collapsedNodeIds.value = new Set(collapsedNodeIds.value)
    }
  })
}

const projectNodesToLayerLanes = (nodes: any[]) => {
  if (!currentTemplate.value || !graphContainer.value) return nodes

  const width = graphContainer.value.clientWidth || 1200
  const height = graphContainer.value.clientHeight || 720
  const layers = currentTemplate.value.layers || []
  const layoutDirection = currentTemplate.value.layoutDirection || 'horizontal'

  const layerCount = Math.max(layers.length, 1)
  const resolveLayerIndex = (modelKey: string) => {
    if (modelKey === 'aggregate') return layerCount - 1
    for (let i = 0; i < layers.length; i += 1) {
      if (layers[i].modelKeys.includes(modelKey)) return i
    }
    return layerCount - 1
  }

  const bucketMap = new Map<number, any[]>()
  nodes.forEach((node) => {
    const idx = resolveLayerIndex(node.modelKey)
    if (!bucketMap.has(idx)) {
      bucketMap.set(idx, [])
    }
    bucketMap.get(idx)?.push(node)
  })

  const topPadding = 72
  const sidePadding = 70
  const bottomPadding = 36
  const placed: any[] = []

  if (layoutDirection === 'vertical') {
    const laneHeight = Math.max((height - topPadding - bottomPadding) / layerCount, 1)
    Array.from(bucketMap.entries()).forEach(([layerIndex, list]) => {
      const sorted = [...list].sort((a, b) => String(a.name).localeCompare(String(b.name)))
      const stepX = Math.max((width - sidePadding * 2) / (sorted.length + 1), 1)
      sorted.forEach((node, row) => {
        placed.push({
          ...node,
          x: sidePadding + stepX * (row + 1),
          y: topPadding + laneHeight * layerIndex + laneHeight / 2
        })
      })
    })
    return placed
  }

  const laneWidth = Math.max((width - sidePadding * 2) / layerCount, 1)
  Array.from(bucketMap.entries()).forEach(([layerIndex, list]) => {
    const sorted = [...list].sort((a, b) => String(a.name).localeCompare(String(b.name)))
    const stepY = Math.max((height - topPadding - bottomPadding) / (sorted.length + 1), 1)
    sorted.forEach((node, row) => {
      placed.push({
        ...node,
        x: sidePadding + laneWidth * layerIndex + laneWidth / 2,
        y: topPadding + stepY * (row + 1)
      })
    })
  })
  return placed
}

const fetchTopologyByTemplate = async () => {
  if (!currentTemplate.value) {
    topologyNodes.value = []
    topologyEdges.value = []
    return
  }
  const seedModelCodes = new Set(currentTemplate.value.seedModels || [])
  const visibleModelCodes = new Set(currentTemplate.value.visibleModelKeys || [])
  const modelIdList = cmdbModels.value
    .filter((item: any) => {
      const code = String(item?.code || '')
      if (!code) return false
      if (visibleModelCodes.size > 0) return visibleModelCodes.has(code)
      return seedModelCodes.has(code)
    })
    .map((item: any) => Number(item.id))
    .filter((id: number) => id > 0)

  const depth = Math.max(1, Math.min(10, (currentTemplate.value.layers?.length || 1) + 1))

  loading.value = true
  try {
    const res = await getTopology({
      model_ids: modelIdList.join(','),
      depth
    })
    if (res.code !== 200) {
      throw new Error(res.message || '拓扑数据加载失败')
    }
    topologyNodes.value = Array.isArray(res.data?.nodes) ? res.data.nodes : []
    topologyEdges.value = Array.isArray(res.data?.edges) ? res.data.edges : []
  } catch (error: any) {
    topologyNodes.value = []
    topologyEdges.value = []
    message.error(error?.message || '拓扑数据加载失败')
  } finally {
    loading.value = false
  }
}

const updateGraph = async () => {
  if (!graph || !renderedData.value.nodes.length) {
    if (graph) graph.setData({ nodes: [], edges: [] })
    return
  }

  loading.value = true
  try {
    const edgeStyleByRelation: Record<string, { stroke: string; lineDash?: number[] }> = {
      RunsOn: { stroke: '#52c41a', lineDash: [4, 2] },
      ConnectTo: { stroke: '#1677ff' },
      DependOn: { stroke: '#fa8c16', lineDash: [8, 4] }
    }

    const projectedNodes = projectNodesToLayerLanes(renderedData.value.nodes)
    const expandableNodeSet = new Set<string>(
      fullExtractedData.value.edges.map((edge: any) => String(edge.source))
    )

    const gData: any = {
      nodes: projectedNodes.map((n: any) => ({
        id: n.id,
        name: n.name,
        status: n.status,
        modelKey: n.modelKey,
        style: {
          x: n.x,
          y: n.y,
          size: 58,
          fill: '#ffffff',
          stroke: n.status === 'ALARM' ? '#ef4444' : (n.id === activeNodeId.value ? '#1677ff' : '#bcd8ff'),
          lineWidth: n.status === 'ALARM' ? 2.6 : (n.id === activeNodeId.value ? 2.6 : 1.8),
          icon: true,
          iconSrc: getNodeIconSrc(n),
          iconWidth: 22,
          iconHeight: 22,
          badges: buildNodeToggleBadges(String(n.id), collapsedNodeIds.value, expandableNodeSet) as any,
          labelText: String(n.primaryText || n.name || ''),
          labelPlacement: 'bottom',
          labelFill: '#1f1f1f',
          labelFontSize: 12,
          shadowColor: n.status === 'ALARM' ? 'rgba(239,68,68,0.35)' : 'rgba(59,130,246,0.2)',
          shadowBlur: n.id === activeNodeId.value ? 16 : 12
        },
        data: { ...n }
      })),
      edges: renderedData.value.edges.map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        relationType: e.type,
        style: {
          ...(edgeStyleByRelation[e.type] || { stroke: '#d9d9d9' }),
          lineWidth: 1,
          endArrow: e.direction !== 'undirected',
          labelText: e.type,
          labelFontSize: 10,
          labelFill: '#8c8c8c',
          labelBackground: true,
          labelBackgroundFill: '#fff'
        }
      }))
    }

    graph.setData(gData)
    await graph.render()
  } finally {
    loading.value = false
  }
}

// --- 工具逻辑 ---
const handleFitView = () => {
  if (!graph) return
  if (typeof graph.zoomTo === 'function') {
    graph.zoomTo(1)
  }
  if (typeof (graph as any).translateTo === 'function') {
    ;(graph as any).translateTo([0, 0])
  } else if (typeof graph.fitCenter === 'function') {
    graph.fitCenter()
  }
}
const expandAll = () => { collapsedNodeIds.value = new Set() }
const collapseToSeed = () => {
  const seeds = fullExtractedData.value.seedNodeIds || []
  collapsedNodeIds.value = new Set(seeds)
}

watch(selectedTemplateId, () => {
  void (async () => {
    collapsedNodeIds.value = new Set()
    activeNodeId.value = ''
    activeNode.value = null
    await fetchTopologyByTemplate()
    await updateGraph()
  })()
})

watch(collapsedNodeIds, () => updateGraph())

const onResize = () => {
  if (graph && graphContainer.value) {
    graph.setSize(graphContainer.value.clientWidth, graphContainer.value.clientHeight)
    updateGraph()
  }
}

onMounted(() => {
  void (async () => {
    const [tplRes, modelRes, relationRes] = await Promise.all([
      listCmdbTopologyTemplates(),
      getModels({ page: 1, per_page: 1000 }),
      getRelationTypes({ page: 1, per_page: 1000 })
    ])
    templates.value = tplRes.code === 200 && Array.isArray(tplRes.data?.items) ? tplRes.data.items : []
    cmdbModels.value = modelRes.code === 200 && Array.isArray(modelRes.data?.items) ? modelRes.data.items : []
    relationTypes.value = relationRes.code === 200 && Array.isArray(relationRes.data?.items) ? relationRes.data.items : []
    const qId = String(route.query.templateId || '')
    if (qId) selectedTemplateId.value = qId
    else if (templates.value.length > 0) selectedTemplateId.value = String(templates.value[0].id)
    nextTick(() => {
      initGraph()
      updateGraph()
      window.addEventListener('resize', onResize)
    })
  })()
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  graph?.destroy()
})

const goTemplateList = () => router.push('/cmdb/topology-template')
const goTemplateEdit = () => router.push(`/cmdb/topology-template/edit/${selectedTemplateId.value}`)

const openCiDetail = () => {
  if (!activeNode.value || activeNode.value.nodeKind === 'aggregate') return
  const ciId = Number(activeNode.value.id)
  if (Number.isNaN(ciId) || ciId <= 0) {
    message.warning('当前节点没有可查看的CI详情')
    return
  }
  currentInstanceId.value = ciId
  detailDrawerVisible.value = true
}

const handleNodeDeleted = () => {
  detailDrawerVisible.value = false
}
</script>

<style scoped>
.topology-render-page { background: transparent; min-height: calc(100vh - 120px); padding: 0; }
.main-card :deep(.ant-card-head) { border-bottom: none; padding-top: 8px; }
.page-title { font-size: 18px; font-weight: 600; color: var(--app-text-primary); }

.graph-wrapper { border: 1px solid var(--app-border); border-radius: 8px; background: var(--app-surface-card); overflow: hidden; }
.graph-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; background: var(--app-surface-subtle); border-bottom: 1px solid var(--app-border);
}
.graph-stats { color: var(--app-text-muted); font-size: 12px; }
.layer-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  padding: 8px 12px;
  background: var(--app-surface-subtle);
  border-bottom: 1px solid var(--app-border);
}
.layer-chip {
  border: 1px solid var(--app-border);
  border-radius: 6px;
  background: var(--app-surface-card);
  padding: 6px 8px;
}
.layer-chip-name { font-weight: 600; font-size: 12px; color: var(--app-text-primary); }
.layer-chip-models { font-size: 12px; color: var(--app-text-secondary); margin-top: 2px; }
.layer-chip-count { font-size: 11px; color: var(--app-text-muted); margin-top: 3px; }
.graph-container {
  width: 100%; height: 720px;
  /* 辅助背景 */
  background-image: 
    linear-gradient(var(--app-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--app-border) 1px, transparent 1px);
  background-size: 40px 40px;
}
.graph-stage {
  position: relative;
}
.layer-overlay {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  display: grid;
}
.overlay-horizontal {
  grid-template-columns: 1fr;
}
.overlay-vertical {
  grid-template-rows: 1fr;
}
.layer-band {
  position: relative;
  border-right: 1px dashed color-mix(in srgb, var(--app-accent) 22%, transparent);
  border-bottom: 1px dashed color-mix(in srgb, var(--app-accent) 18%, transparent);
  background: color-mix(in srgb, var(--app-accent) 4%, transparent);
}
.overlay-horizontal .layer-band:last-child {
  border-right: none;
}
.overlay-vertical .layer-band:last-child {
  border-bottom: none;
}
.layer-band-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 6px;
  padding: 3px 10px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--app-surface-card) 92%, transparent);
  border: 1px solid color-mix(in srgb, var(--app-accent) 18%, transparent);
  font-size: 12px;
  font-weight: 600;
  color: var(--app-text-primary);
}

.ci-header { display: flex; align-items: center; gap: 12px; }
.ci-icon {
  width: 36px; height: 36px; border-radius: 6px; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: bold;
}
.ci-name { font-weight: 600; font-size: 15px; color: var(--app-text-primary); }
.ci-type { font-size: 12px; color: var(--app-text-muted); }
.info-card { border-radius: 8px; box-shadow: var(--app-shadow-sm); }

.loading-tag { font-size: 12px; color: var(--app-accent); }
</style>
