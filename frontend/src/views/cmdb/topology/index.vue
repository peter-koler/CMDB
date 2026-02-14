<template>
  <div class="topology-page">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[16, 16]" style="width: 100%">
          <a-col :xs="24" :sm="12" :md="6">
            <a-form-item label="关键词">
              <a-input
                v-model:value="searchKeyword"
                placeholder="请输入CI名称或编码"
                allowClear
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
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
          <a-col :xs="24" :sm="12" :md="6">
            <a-form-item label="布局">
              <a-select v-model:value="layout" placeholder="布局算法" style="width: 100%">
                <a-select-option value="force">力导向</a-select-option>
                <a-select-option value="dagre">层级</a-select-option>
                <a-select-option value="circular">环形</a-select-option>
                <a-select-option value="grid">网格</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="24" :md="6">
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
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-row :gutter="16">
      <a-col :xs="24" :sm="8" :md="6">
        <a-card title="节点列表" :bordered="false" class="nodes-card">
          <a-list
            :data-source="nodes"
            :loading="loading"
            size="small"
          >
            <template #renderItem="{ item }">
              <a-list-item @click="focusNode(item)" :class="{ selected: selectedNodeId === item.id }">
                <a-space>
                  <div
                    class="node-color-dot"
                    :style="{ backgroundColor: getNodeColor(item) }"
                  ></div>
                  <span class="node-name">{{ item.name }}</span>
                </a-space>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <a-col :xs="24" :sm="16" :md="18">
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
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  SearchOutlined,
  ReloadOutlined,
  SyncOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined
} from '@ant-design/icons-vue'
import G6 from '@antv/g6'
import { getTopology } from '@/api/cmdb-relation'
import { getModels } from '@/api/cmdb'

const loading = ref(false)
const searchKeyword = ref('')
const searchModelId = ref<number | null>(null)
const layout = ref('force')
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const models = ref<any[]>([])
const selectedNodeId = ref<number | null>(null)
const graphContainer = ref<HTMLElement>()
let graph: any = null

const modelColorMap: Record<number, string> = {}

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

const initGraph = () => {
  if (!graphContainer.value) return

  graph = new G6.Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: graphContainer.value.clientHeight - 24,
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node']
    },
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
  })

  graph.on('node:click', (evt: any) => {
    const node = evt.item
    if (node) {
      const model = node.getModel()
      selectedNodeId.value = model.id
      graph.setItemState(node, 'selected', true)
    }
  })

  graph.on('canvas:click', () => {
    selectedNodeId.value = null
    graph.clearItemStates()
  })

  renderGraph()
}

const renderGraph = () => {
  if (!graph) return

  const graphNodes = nodes.value.map((node) => ({
    id: String(node.id),
    label: node.name,
    model_id: node.model_id,
    style: {
      fill: getNodeColor(node)
    }
  }))

  const graphEdges = edges.value.map((edge, index) => ({
    id: String(edge.id || index),
    source: String(edge.source),
    target: String(edge.target),
    label: edge.relation_type_name || '',
    style: {
      endArrow: edge.direction === 'directed' ? true : false
    }
  }))

  graph.changeData({
    nodes: graphNodes,
    edges: graphEdges
  })
}

const fetchTopology = async () => {
  loading.value = true
  try {
    const res = await getTopology({
      model_id: searchModelId.value,
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

const focusNode = (node: any) => {
  selectedNodeId.value = node.id
  if (graph) {
    graph.focusItem(String(node.id), true)
  }
}

const handleSearch = () => {
  fetchTopology()
}

const handleReset = () => {
  searchKeyword.value = ''
  searchModelId.value = null
  fetchTopology()
}

const handleRefresh = () => {
  fetchTopology()
}

const zoomIn = () => {
  if (graph) {
    const currentZoom = graph.getZoom()
    graph.zoomTo(currentZoom * 1.2)
  }
}

const zoomOut = () => {
  if (graph) {
    const currentZoom = graph.getZoom()
    graph.zoomTo(currentZoom * 0.8)
  }
}

const fitView = () => {
  if (graph) {
    graph.fitView()
  }
}

const handleResize = () => {
  if (graph && graphContainer.value) {
    graph.changeSize(graphContainer.value.clientWidth, graphContainer.value.clientHeight - 24)
  }
}

watch(layout, () => {
  if (graph) {
    graph.updateLayout({
      type: layout.value,
      preventOverlap: true,
      nodeSpacing: 100,
      linkDistance: 150
    })
  }
})

onMounted(() => {
  fetchModels()
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

.nodes-card {
  height: 100%;
  overflow: auto;
}

.nodes-card :deep(.ant-list-item) {
  cursor: pointer;
  transition: all 0.3s;
}

.nodes-card :deep(.ant-list-item:hover) {
  background: #f5f5f5;
}

.nodes-card :deep(.ant-list-item.selected) {
  background: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.node-color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
