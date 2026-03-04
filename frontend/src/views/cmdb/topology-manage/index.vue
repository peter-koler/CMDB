<template>
  <div class="topology-render-page">
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
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Graph } from '@antv/g6'
import { useRoute, useRouter } from 'vue-router'
import {
  buildRenderedGraphData,
  CiNode,
  extractByTemplate,
  getTopologyTemplate,
  listTopologyTemplates,
  modelDefs,
  TopologyTemplate
} from '@/mock/topology-template'

const route = useRoute()
const router = useRouter()
const graphContainer = ref<HTMLElement>()
const loading = ref(false)

// --- 状态数据 ---
const templates = ref<TopologyTemplate[]>([])
const selectedTemplateId = ref('')
const activeNode = ref<CiNode | null>(null)
const activeNodeId = ref('')
const collapsedNodeIds = ref<Set<string>>(new Set())
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
const currentTemplate = computed(() => templates.value.find(t => t.id === selectedTemplateId.value))
const renderedData = computed(() => {
  if (!currentTemplate.value) return { nodes: [], edges: [], combos: [] }
  return buildRenderedGraphData(currentTemplate.value, collapsedNodeIds.value)
})
const fullExtractedData = computed(() => {
  if (!currentTemplate.value) return { nodes: [], edges: [], seedNodeIds: [] as string[] }
  return extractByTemplate(currentTemplate.value, new Set())
})
const stats = computed(() => ({
  nodeCount: renderedData.value.nodes?.length || 0,
  edgeCount: renderedData.value.edges?.length || 0
}))
const getModelLabel = (key: string) => modelDefs.find(m => m.key === key)?.label || (key === 'aggregate' ? '聚合池' : key)

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
    // 节点样式升级
    node: {
      style: {
        size: [120, 40], // 采用长方形卡片风格
        type: 'rect',
        radius: 4,
        fill: '#ffffff',
        stroke: (d: any) => d.status === 'ALARM' ? '#ff4d4f' : '#e8e8e8',
        lineWidth: (d: any) => d.status === 'ALARM' ? 2 : 1,
        // 节点内文字
        labelText: (d: any) => {
          const raw = String(d.name || '')
          const markerMatch = raw.match(/\s(\[\+\]|\[-\])$/)
          const marker = markerMatch ? markerMatch[1] : ''
          const base = markerMatch ? raw.replace(/\s(\[\+\]|\[-\])$/, '') : raw
          const shortBase = base.length > 12 ? `${base.substring(0, 10)}...` : base
          return marker ? `${shortBase} ${marker}` : shortBase
        },
        labelFill: '#262626',
        labelFontSize: 13,
        labelPlacement: 'center',
        // 增加左侧装饰色条
        iconText: ' ',
        iconFontSize: 12,
        shadowColor: 'rgba(0,0,0,0.04)',
        shadowBlur: 8,
        cursor: 'pointer',
      },
      state: {
        selected: { stroke: '#1677ff', lineWidth: 2, fill: '#f0f7ff' },
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

  graph.on('node:click', (evt) => {
    const nodeId = String(evt.target.id)
    activeNodeId.value = nodeId
    activeNode.value = renderedData.value.nodes.find((n: any) => n.id === nodeId) || null

    const isCollapsed = collapsedNodeIds.value.has(nodeId)
    const hasChildrenInFullGraph = fullExtractedData.value.edges.some((edge: any) => edge.source === nodeId)
    if (isCollapsed) {
      collapsedNodeIds.value.delete(nodeId)
      collapsedNodeIds.value = new Set(collapsedNodeIds.value)
      return
    }
    if (hasChildrenInFullGraph) {
      collapsedNodeIds.value.add(nodeId)
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

    const gData = {
      nodes: projectedNodes.map((n: any) => ({
        id: n.id,
        name: (() => {
          const baseName = n.nodeKind === 'aggregate' ? `📦 ${n.name} (${n.count})` : `🔹 ${n.name}`
          if (!expandableNodeSet.has(String(n.id))) return baseName
          return `${baseName} ${collapsedNodeIds.value.has(String(n.id)) ? '[+]' : '[-]'}`
        })(),
        status: n.status,
        modelKey: n.modelKey,
        style: {
          x: n.x,
          y: n.y,
          stroke: n.id === activeNodeId.value ? '#1677ff' : undefined,
          lineWidth: n.id === activeNodeId.value ? 2 : undefined
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
          endArrow: true,
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
  const seeds = renderedData.value.extracted?.seedNodeIds || []
  collapsedNodeIds.value = new Set(seeds)
}

watch([selectedTemplateId, collapsedNodeIds], () => updateGraph())

const onResize = () => {
  if (graph && graphContainer.value) {
    graph.setSize(graphContainer.value.clientWidth, graphContainer.value.clientHeight)
    updateGraph()
  }
}

onMounted(() => {
  templates.value = listTopologyTemplates()
  const qId = route.query.templateId as string
  if (qId) selectedTemplateId.value = qId
  else if (templates.value.length > 0) selectedTemplateId.value = templates.value[0].id

  nextTick(() => {
    initGraph()
    updateGraph()
    window.addEventListener('resize', onResize)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  graph?.destroy()
})

const goTemplateList = () => router.push('/cmdb/topology-template')
const goTemplateEdit = () => router.push(`/cmdb/topology-template/edit/${selectedTemplateId.value}`)
</script>

<style scoped>
.topology-render-page { background: #f0f2f5; min-height: calc(100vh - 120px); padding: 16px; }
.main-card :deep(.ant-card-head) { border-bottom: none; padding-top: 8px; }
.page-title { font-size: 18px; font-weight: 600; color: #1f1f1f; }

.graph-wrapper { border: 1px solid #e8e8e8; border-radius: 8px; background: #fff; overflow: hidden; }
.graph-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #e8e8e8;
}
.graph-stats { color: #8c8c8c; font-size: 12px; }
.layer-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  padding: 8px 12px;
  background: #fcfcfc;
  border-bottom: 1px solid #f0f0f0;
}
.layer-chip {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  background: #fff;
  padding: 6px 8px;
}
.layer-chip-name { font-weight: 600; font-size: 12px; color: #1f1f1f; }
.layer-chip-models { font-size: 12px; color: #595959; margin-top: 2px; }
.layer-chip-count { font-size: 11px; color: #8c8c8c; margin-top: 3px; }
.graph-container {
  width: 100%; height: 720px;
  /* 辅助背景 */
  background-image: 
    linear-gradient(#f9f9f9 1px, transparent 1px),
    linear-gradient(90deg, #f9f9f9 1px, transparent 1px);
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
  border-right: 1px dashed rgba(22, 119, 255, 0.22);
  border-bottom: 1px dashed rgba(22, 119, 255, 0.18);
  background: rgba(22, 119, 255, 0.025);
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
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(22, 119, 255, 0.18);
  font-size: 12px;
  font-weight: 600;
  color: #1f1f1f;
}

.ci-header { display: flex; align-items: center; gap: 12px; }
.ci-icon {
  width: 36px; height: 36px; border-radius: 6px; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: bold;
}
.ci-name { font-weight: 600; font-size: 15px; color: #262626; }
.ci-type { font-size: 12px; color: #8c8c8c; }
.info-card { border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }

.loading-tag { font-size: 12px; color: #1677ff; }
</style>
