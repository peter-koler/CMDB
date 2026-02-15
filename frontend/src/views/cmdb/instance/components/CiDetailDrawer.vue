<template>
  <a-drawer
    :open="visible"
    :title="`CI详情 - ${ciData?.name || ''}`"
    :width="1000"
    @close="handleClose"
    :body-style="{ paddingBottom: '80px' }"
  >
    <template #extra>
      <a-space>
        <a-button type="primary" @click="handleEdit">编辑</a-button>
        <a-button danger @click="checkAndDelete">删除</a-button>
      </a-space>
    </template>

    <!-- 删除确认弹窗 -->
    <a-modal
      v-model:open="deleteModalVisible"
      title="确认删除"
      @ok="confirmDelete"
      :confirm-loading="deleteLoading"
    >
      <a-alert
        v-if="relationsCount.total > 0"
        type="warning"
        :message="`该CI存在 ${relationsCount.total} 个关联关系`"
        :description="`其中 ${relationsCount.out_relations} 个出边关系（依赖其他CI），${relationsCount.in_relations} 个入边关系（被其他CI依赖）。删除CI将同时删除这些关系，是否继续？`"
        show-icon
        style="margin-bottom: 16px"
      />
      <p v-else>确定要删除此CI吗？删除后无法恢复。</p>
    </a-modal>

    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="basic" tab="基本信息">
        <a-descriptions :column="1" bordered size="small">
          <a-descriptions-item label="CI编码">
            {{ ciData?.code || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="CI名称">
            {{ ciData?.name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="所属模型">
            {{ ciData?.model?.name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="所属部门">
            {{ ciData?.department?.name || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="创建人">
            {{ ciData?.creator?.username || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">
            {{ ciData?.created_at ? formatDateTime(ciData.created_at) : '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="更新时间">
            {{ ciData?.updated_at ? formatDateTime(ciData.updated_at) : '-' }}
          </a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>

      <a-tab-pane key="attributes" tab="属性信息">
        <div v-if="modelFields.length === 0" class="attributes-empty">
          暂无属性信息
        </div>
        <div v-else class="attributes-layout">
          <div
            v-for="section in attributeSections"
            :key="section.key"
            class="attributes-section-simple"
          >
            <div v-if="section.title && attributeSections.length > 1" class="attributes-section-title">
              {{ section.title }}
            </div>
            <a-row :gutter="[12, 12]">
              <a-col
                v-for="field in section.fields"
                :key="field.code"
                :xs="24"
                :sm="getFieldCol(field)"
              >
                <div class="attribute-line">
                  <span class="attribute-line-label">
                    {{ field.name }}<span v-if="field.required" style="color:#f5222d;">*</span>：
                  </span>
                  <div class="attribute-line-value-box">
                    <template v-if="field.field_type === 'boolean'">
                      {{ getFieldValue(field.code) ? '是' : '否' }}
                    </template>
                    <template v-else-if="field.field_type === 'image'">
                      <a-image
                        v-if="getFieldValue(field.code)"
                        :src="getFieldValue(field.code)"
                        :width="96"
                      />
                      <span v-else class="empty-value">-</span>
                    </template>
                    <template v-else-if="field.field_type === 'file'">
                      <a-button
                        v-if="getFieldValue(field.code)"
                        type="link"
                        size="small"
                        @click="downloadFile(getFieldValue(field.code))"
                      >
                        下载文件
                      </a-button>
                      <span v-else class="empty-value">-</span>
                    </template>
                    <template v-else>
                      {{ formatFieldDisplay(field, getFieldValue(field.code)) }}
                    </template>
                  </div>
                </div>
              </a-col>
            </a-row>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="history" tab="变更历史">
        <a-table
          :columns="historyColumns"
          :data-source="historyList"
          :loading="historyLoading"
          :pagination="historyPagination"
          row-key="id"
          size="small"
          @change="handleHistoryTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'operation'">
              <a-tag :color="getHistoryColor(record.operation)">
                {{ getOperationText(record.operation) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'change'">
              <div v-if="record.old_value || record.new_value">
                <span v-if="record.old_value" style="color: #cf132d; text-decoration: line-through;">
                  {{ truncate(record.old_value, 50) }}
                </span>
                <span v-if="record.old_value && record.new_value"> → </span>
                <span v-if="record.new_value" style="color: #3f8600;">
                  {{ truncate(record.new_value, 50) }}
                </span>
              </div>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDateTime(record.created_at) }}
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="relations" tab="关系管理">
        <a-card :bordered="false" style="margin-bottom: 16px;">
          <a-space wrap>
            <a-select
              v-model:value="relationDepth"
              style="width: 120px"
              placeholder="展开层级"
              @change="fetchRelations"
            >
              <a-select-option :value="1">1层</a-select-option>
              <a-select-option :value="2">2层</a-select-option>
              <a-select-option :value="3">3层</a-select-option>
              <a-select-option :value="4">4层</a-select-option>
            </a-select>
            <a-button type="primary" @click="showAddRelationModal">
              <template #icon><PlusOutlined /></template>
              新增关系
            </a-button>
          </a-space>
        </a-card>

        <a-tabs v-model:activeKey="relationViewTab">
          <a-tab-pane key="list" tab="关系列表">
            <a-table
              :columns="relationColumns"
              :data-source="relationList"
              :loading="relationsLoading"
              :pagination="false"
              row-key="row_key"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'direction'">
                  <a-tag :color="record.direction === 'out' ? 'blue' : 'geekblue'">
                    {{ record.direction === 'out' ? '依赖' : '被依赖' }}
                  </a-tag>
                </template>
                <template v-else-if="column.key === 'peer_ci_name'">
                  {{ record.peer_display || record.peer_ci_name || '-' }}
                </template>
                <template v-else-if="column.key === 'source_type'">
                  <a-tag :color="getSourceTypeColor(record.source_type)">
                    {{ getSourceTypeText(record.source_type) }}
                  </a-tag>
                </template>
                <template v-else-if="column.key === 'created_at'">
                  {{ formatDateTime(record.created_at) }}
                </template>
                <template v-else-if="column.key === 'action'">
                  <a-popconfirm
                    title="确定删除该关系吗？"
                    @confirm="deleteRelation(record.id)"
                  >
                    <a-button type="link" size="small" danger>
                      删除
                    </a-button>
                  </a-popconfirm>
                </template>
              </template>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="topology" tab="拓扑图">
            <a-card :bordered="false">
              <template #extra>
                <a-space>
                  <a-button size="small" @click="zoomIn">
                    <ZoomInOutlined /> 放大
                  </a-button>
                  <a-button size="small" @click="zoomOut">
                    <ZoomOutOutlined /> 缩小
                  </a-button>
                  <a-button size="small" @click="fitView">
                    <FullscreenOutlined /> 自适应
                  </a-button>
                </a-space>
              </template>
              <div ref="graphContainer" class="ci-graph-container"></div>
              <div v-if="selectedTopologyNode" class="topology-node-panel">
                <a-descriptions title="节点信息" :column="1" size="small" bordered>
                  <a-descriptions-item label="模型图标">
                    <img
                      v-if="selectedTopologyNode.model_icon_url"
                      :src="selectedTopologyNode.model_icon_url"
                      style="width: 18px; height: 18px; object-fit: contain;"
                    />
                    <component v-else :is="selectedTopologyNode.model_icon || 'AppstoreOutlined'" />
                  </a-descriptions-item>
                  <a-descriptions-item label="CI名称">
                    {{ selectedTopologyNode.name || '-' }}
                  </a-descriptions-item>
                  <a-descriptions-item label="CI编码">
                    {{ selectedTopologyNode.code || '-' }}
                  </a-descriptions-item>
                  <a-descriptions-item label="模型">
                    {{ selectedTopologyNode.model_name || '-' }}
                  </a-descriptions-item>
                  <a-descriptions-item label="关键属性值">
                    {{
                      Array.isArray(selectedTopologyNode.display_subtitles) && selectedTopologyNode.display_subtitles.length
                        ? selectedTopologyNode.display_subtitles.join(' | ')
                        : selectedTopologyNode.code || '-'
                    }}
                  </a-descriptions-item>
                </a-descriptions>
                <div class="topology-node-actions">
                  <a-button type="primary" size="small" @click="openTopologyNodeDetail">
                    查看详情
                  </a-button>
                </div>
              </div>
            </a-card>
          </a-tab-pane>
        </a-tabs>
      </a-tab-pane>
    </a-tabs>

    <a-modal
      v-model:open="addRelationModalVisible"
      title="新增关系"
      @ok="handleAddRelation"
      :confirm-loading="addRelationLoading"
    >
      <a-form :model="addRelationForm" ref="addRelationFormRef" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
        <a-form-item label="关系类型" name="relation_type_id">
          <a-select v-model:value="addRelationForm.relation_type_id" placeholder="请选择关系类型" style="width: 100%">
            <a-select-option v-for="rt in relationTypes" :key="rt.id" :value="rt.id">
              {{ rt.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标CI" name="target_ci_id">
          <a-select
            v-model:value="addRelationForm.target_ci_id"
            placeholder="请选择目标CI"
            style="width: 100%"
            :filter-option="filterCiOption"
            show-search
          >
            <a-select-option v-for="ci in candidateCis" :key="ci.id" :value="ci.id">
              {{ ci.code }} - {{ ci.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, reactive, nextTick, onUnmounted, createApp, h } from 'vue'
import { message } from 'ant-design-vue'
import { getInstanceDetail, getCiHistory, deleteInstance, getInstances, getInstanceRelationsCount } from '@/api/ci'
import { getInstanceRelations, createRelation, deleteRelation as deleteRelationApi, getRelationTypes } from '@/api/cmdb-relation'
import {
  PlusOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  ApiOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  ContainerOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  GlobalOutlined,
  HddOutlined,
  LaptopOutlined
} from '@ant-design/icons-vue'
import { Graph } from '@antv/g6'
import dayjs from 'dayjs'

interface Props {
  visible: boolean
  instanceId: number | null
}

const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'edit', 'deleted'])
const currentInstanceId = ref<number | null>(null)

const activeTab = ref('basic')
const ciData = ref<any>(null)
const modelFields = ref<any[]>([])
const attributeSections = ref<any[]>([])
const historyList = ref<any[]>([])
const loading = ref(false)
const historyLoading = ref(false)

const relationsLoading = ref(false)
const relationDepth = ref(1)
const relationViewTab = ref('list')
const outRelations = ref<any[]>([])
const inRelations = ref<any[]>([])
const relationTypes = ref<any[]>([])
const candidateCis = ref<any[]>([])

const addRelationModalVisible = ref(false)
const addRelationLoading = ref(false)
const addRelationFormRef = ref()
const addRelationForm = reactive({
  relation_type_id: null as number | null,
  target_ci_id: null as number | null
})

// 删除确认弹窗相关
const deleteModalVisible = ref(false)
const deleteLoading = ref(false)
const relationsCount = reactive({
  total: 0,
  out_relations: 0,
  in_relations: 0
})

// 拓扑图相关
const graphContainer = ref<HTMLElement>()
let graph: any = null
const graphNodes = ref<any[]>([])
const graphEdges = ref<any[]>([])
const selectedTopologyNode = ref<any>(null)
const getActiveInstanceId = () => currentInstanceId.value ?? props.instanceId

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
    if (typeof graph.render === 'function') {
      graph.render()
    } else if (typeof graph.draw === 'function') {
      graph.draw()
    }
  }
}

const initGraph = () => {
  if (!graphContainer.value) return

  graph = new Graph({
    container: graphContainer.value,
    width: graphContainer.value.clientWidth,
    height: 400,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    defaultNode: {
      size: 36,
      style: {
        lineWidth: 0
      },
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
      const targetNode = graphNodes.value.find(
        (item: any) => String(item.id) === String(model.id)
      ) || null
      selectedTopologyNode.value = targetNode
      if (targetNode?.id) {
        openTopologyNodeDetail(targetNode.id)
      }
    }
  })

  graph.on('canvas:click', () => {
    selectedTopologyNode.value = null
  })

  renderGraph()
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

  applyGraphData({
    nodes,
    edges
  })
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

const buildTopologyGraphData = () => {
  if (!getActiveInstanceId() || !ciData.value) return
  const nodes: any[] = []
  const edges: any[] = []
  const nodeIds = new Set<number>()

  nodes.push({
    id: ciData.value.id,
    name: ciData.value.name,
    code: ciData.value.code,
    model_id: ciData.value.model_id,
    model_icon: ciData.value.model?.icon || 'AppstoreOutlined',
    model_icon_url: ciData.value.model?.icon_url || '',
    display_title: ciData.value.name || '',
    display_subtitles: [],
    model_name: ciData.value.model?.name || '',
    is_center: true
  })
  nodeIds.add(ciData.value.id)

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
      source: ciData.value?.id,
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
      target: ciData.value?.id,
      relation_type_name: rel.relation_type_name,
      source_type: rel.source_type,
      direction: 'directed'
    })
  })

  graphNodes.value = nodes
  graphEdges.value = edges
  selectedTopologyNode.value = nodes.find((item: any) => item.is_center) || null
}

watch(() => relationViewTab.value, (val) => {
  if (val === 'topology' && getActiveInstanceId()) {
    nextTick(() => {
      if (!graph) {
        initGraph()
      }
      buildTopologyGraphData()
      renderGraph()
    })
  } else {
    selectedTopologyNode.value = null
  }
})

watch([outRelations, inRelations], () => {
  if (relationViewTab.value !== 'topology') return
  buildTopologyGraphData()
  nextTick(() => renderGraph())
})

onUnmounted(() => {
  if (graph) {
    graph.destroy()
    graph = null
  }
})

const relationList = computed(() => {
  const outList = outRelations.value.map((rel: any) => ({
    ...rel,
    row_key: `out_${rel.id}`,
    direction: 'out',
    peer_ci_id: rel.target_ci_id,
    peer_ci_name: rel.target_ci_name,
    peer_ci_code: rel.target_ci_code,
    peer_ci_model_name: rel.target_ci_model_name,
    peer_display: Array.isArray(rel.target_display_subtitles) && rel.target_display_subtitles.length
      ? rel.target_display_subtitles.join(' | ')
      : rel.target_display_title || rel.target_ci_name
  }))
  const inList = inRelations.value.map((rel: any) => ({
    ...rel,
    row_key: `in_${rel.id}`,
    direction: 'in',
    peer_ci_id: rel.source_ci_id,
    peer_ci_name: rel.source_ci_name,
    peer_ci_code: rel.source_ci_code,
    peer_ci_model_name: rel.source_ci_model_name,
    peer_display: Array.isArray(rel.source_display_subtitles) && rel.source_display_subtitles.length
      ? rel.source_display_subtitles.join(' | ')
      : rel.source_display_title || rel.source_ci_name
  }))
  return [...outList, ...inList].sort((a: any, b: any) => {
    return String(b.created_at || '').localeCompare(String(a.created_at || ''))
  })
})

const relationColumns = [
  { title: '方向', key: 'direction', width: 90 },
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name', width: 140 },
  { title: '关联CI', dataIndex: 'peer_ci_name', key: 'peer_ci_name' },
  { title: 'CI编码', dataIndex: 'peer_ci_code', key: 'peer_ci_code', width: 140 },
  { title: '模型', dataIndex: 'peer_ci_model_name', key: 'peer_ci_model_name', width: 120 },
  { title: '来源', dataIndex: 'source_type', key: 'source_type', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '操作', key: 'action', width: 80 }
]

const historyPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})

const historyColumns = [
  { title: '操作类型', dataIndex: 'operation', key: 'operation', width: 100 },
  { title: '属性名称', dataIndex: 'attribute_name', key: 'attribute_name', width: 120 },
  { title: '变更内容', key: 'change' },
  { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 100 },
  { title: '操作时间', dataIndex: 'created_at', key: 'created_at', width: 160 }
]

const attributeValues = computed(() => {
  try {
    return ciData.value?.attributes || ciData.value?.attribute_values || {}
  } catch {
    return {}
  }
})

const getFieldValue = (code: string) => {
  return attributeValues.value?.[code]
}

const getFieldCol = (field: any) => {
  const span = Number(field?.span) || 12
  if ([24, 12, 8, 6].includes(span)) return span
  if (span >= 18) return 24
  if (span >= 10) return 12
  if (span >= 7) return 8
  return 6
}

const isValuePresent = (value: any): boolean => {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return value.trim() !== ''
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value).length > 0
  return true
}

const parseMaybeJson = (value: any) => {
  let parsed = value
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    } catch {
      return value
    }
  }
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    } catch {
      return parsed
    }
  }
  return parsed
}

const buildFormField = (item: any, indexKey: string) => {
  const props = item?.props || {}
  const code = props.code || item?.id || ''
  if (!code || item?.controlType === 'table' || item?.controlType === 'group') return null
  return {
    id: item.id || `field_${indexKey}`,
    code,
    name: props.label || code,
    control_type: item.controlType || 'text',
    field_type: mapControlTypeToFieldType(item.controlType),
    span: Number(props.span) || 12,
    required: !!props.required,
    helpText: props.helpText || '',
    description: props.description || '',
    options: Array.isArray(props.options) ? props.options : []
  }
}

const buildAttributeSchema = (formConfig: any) => {
  const parsed = parseMaybeJson(formConfig)
  if (!Array.isArray(parsed)) {
    return { fields: [], sections: [] }
  }

  const fields: any[] = []
  const sections: any[] = []
  const defaultSectionFields: any[] = []

  parsed.forEach((item: any, index: number) => {
    if (item?.controlType === 'group' && Array.isArray(item.children)) {
      const groupFields = item.children
        .map((child: any, childIndex: number) => buildFormField(child, `${index}_${childIndex}`))
        .filter(Boolean)
      if (groupFields.length > 0) {
        fields.push(...groupFields)
        sections.push({
          key: `group_${index}`,
          title: item?.props?.label || `属性分组 ${index + 1}`,
          fields: groupFields
        })
      }
      return
    }
    const field = buildFormField(item, String(index))
    if (field) {
      fields.push(field)
      defaultSectionFields.push(field)
    }
  })

  if (defaultSectionFields.length > 0) {
    sections.unshift({
      key: 'default_fields',
      title: '基础属性',
      fields: defaultSectionFields
    })
  }

  return { fields, sections }
}

const formatFieldDisplay = (field: any, rawValue: any) => {
  if (!isValuePresent(rawValue)) return '-'

  if (field.field_type === 'date') return formatDate(rawValue)
  if (field.field_type === 'datetime') return formatDateTime(rawValue)
  if (field.field_type === 'numberRange') {
    if (typeof rawValue === 'string') return rawValue
    if (typeof rawValue === 'object' && rawValue !== null) {
      const min = rawValue.min ?? rawValue.start ?? ''
      const max = rawValue.max ?? rawValue.end ?? ''
      return `${min} - ${max}`.trim()
    }
  }

  if (field.field_type === 'select' || field.field_type === 'multiselect') {
    const options = Array.isArray(field.options) ? field.options : []
    const optionMap = new Map(options.map((opt: any) => [String(opt.value), opt.label || opt.value]))
    if (Array.isArray(rawValue)) {
      return rawValue.map((v) => optionMap.get(String(v)) || v).join('，')
    }
    return optionMap.get(String(rawValue)) || String(rawValue)
  }

  if (Array.isArray(rawValue)) return rawValue.join('，')
  if (typeof rawValue === 'object') {
    try {
      return JSON.stringify(rawValue)
    } catch {
      return String(rawValue)
    }
  }

  return String(rawValue)
}

watch(() => props.instanceId, async (val) => {
  currentInstanceId.value = val || null
  if (val && props.visible) {
    await fetchDetail()
    await fetchHistory()
  }
})

watch(() => props.visible, (val) => {
  if (val) {
    currentInstanceId.value = props.instanceId || null
    activeTab.value = 'basic'
    historyPagination.value = { current: 1, pageSize: 10, total: 0 }
    if (getActiveInstanceId()) {
      fetchDetail()
      fetchHistory()
    }
  }
})

const fetchDetail = async () => {
  const instanceId = getActiveInstanceId()
  if (!instanceId) return

  loading.value = true
  try {
    const res = await getInstanceDetail(instanceId)
    
    if (res.code === 200) {
      ciData.value = res.data
      const formConfig = res.data.model?.form_config
      if (formConfig) {
        const schema = buildAttributeSchema(formConfig)
        modelFields.value = schema.fields
        attributeSections.value = schema.sections
      } else {
        const fields = (res.data.model?.fields || []).map((field: any) => ({
          id: field.id || field.code,
          code: field.code,
          name: field.name || field.code,
          field_type: field.field_type || 'text',
          control_type: field.field_type || 'text',
          span: 12,
          required: false,
          helpText: '',
          description: '',
          options: []
        }))
        modelFields.value = fields
        attributeSections.value = fields.length
          ? [{ key: 'default_fields', title: '基础属性', fields }]
          : []
      }
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchHistory = async () => {
  const instanceId = getActiveInstanceId()
  if (!instanceId) return

  historyLoading.value = true
  try {
    const res = await getCiHistory(instanceId)
    if (res.code === 200) {
      historyList.value = res.data || []
      historyPagination.value.total = historyList.value.length
    }
  } catch (error) {
    console.error(error)
  } finally {
    historyLoading.value = false
  }
}

const handleHistoryTableChange = (pag: any) => {
  historyPagination.value.current = pag.current
  historyPagination.value.pageSize = pag.pageSize
}

const handleClose = () => {
  emit('update:visible', false)
}

const handleEdit = () => {
  emit('edit', ciData.value)
  handleClose()
}

// 检查关系并显示删除确认弹窗
const checkAndDelete = async () => {
  const instanceId = getActiveInstanceId()
  if (!instanceId) return
  
  try {
    const res = await getInstanceRelationsCount(instanceId)
    if (res.code === 200) {
      relationsCount.total = res.data.total
      relationsCount.out_relations = res.data.out_relations
      relationsCount.in_relations = res.data.in_relations
      deleteModalVisible.value = true
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '检查关系失败')
  }
}

// 确认删除
const confirmDelete = async () => {
  const instanceId = getActiveInstanceId()
  if (!instanceId) return
  
  deleteLoading.value = true
  try {
    const res = await deleteInstance(instanceId)
    if (res.code === 200) {
      message.success('删除成功')
      deleteModalVisible.value = false
      emit('deleted')
      handleClose()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  } finally {
    deleteLoading.value = false
  }
}

const formatDateTime = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const formatDate = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD')
}

const getHistoryColor = (operation: string) => {
  const colorMap: Record<string, string> = {
    'CREATE': 'green',
    'UPDATE': 'blue',
    'DELETE': 'red'
  }
  return colorMap[operation] || 'gray'
}

const getOperationText = (operation: string) => {
  const textMap: Record<string, string> = {
    'CREATE': '创建',
    'UPDATE': '更新',
    'DELETE': '删除'
  }
  return textMap[operation] || operation
}

const mapControlTypeToFieldType = (controlType: string): string => {
  const typeMap: Record<string, string> = {
    'text': 'text',
    'textarea': 'text',
    'number': 'number',
    'date': 'date',
    'datetime': 'datetime',
    'select': 'select',
    'radio': 'select',
    'checkbox': 'multiselect',
    'switch': 'boolean',
    'user': 'user',
    'reference': 'reference',
    'image': 'image',
    'file': 'file',
    'numberRange': 'numberRange'
  }
  return typeMap[controlType] || 'text'
}

const downloadFile = (url: string) => {
  window.open(url, '_blank')
}

const truncate = (str: string, maxLen: number) => {
  if (!str) return ''
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str
}

watch(activeTab, (val) => {
  if (val === 'history' && getActiveInstanceId()) {
    fetchHistory()
  }
  if (val === 'relations' && getActiveInstanceId()) {
    fetchRelations()
  }
})

const fetchRelations = async () => {
  const instanceId = getActiveInstanceId()
  if (!instanceId) return
  relationsLoading.value = true
  try {
    const res = await getInstanceRelations(instanceId, { depth: relationDepth.value })
    if (res.code === 200) {
      outRelations.value = res.data.out_relations || []
      inRelations.value = res.data.in_relations || []
    }
  } catch (error) {
    console.error(error)
  } finally {
    relationsLoading.value = false
  }
}

const fetchRelationTypes = async () => {
  try {
    const res = await getRelationTypes({ per_page: 1000 })
    if (res.code === 200) {
      relationTypes.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchCandidateCis = async () => {
  const instanceId = getActiveInstanceId()
  try {
    const res = await getInstances({ per_page: 1000 })
    if (res.code === 200) {
      candidateCis.value = res.data.items.filter((ci: any) => ci.id !== instanceId)
    }
  } catch (error) {
    console.error(error)
  }
}

const showAddRelationModal = () => {
  fetchRelationTypes()
  fetchCandidateCis()
  addRelationForm.relation_type_id = null
  addRelationForm.target_ci_id = null
  addRelationModalVisible.value = true
}

const handleAddRelation = async () => {
  const instanceId = getActiveInstanceId()
  if (!addRelationForm.relation_type_id || !addRelationForm.target_ci_id) {
    message.warning('请填写完整信息')
    return
  }
  if (!instanceId) return

  addRelationLoading.value = true
  try {
    const res = await createRelation({
      source_ci_id: instanceId,
      target_ci_id: addRelationForm.target_ci_id,
      relation_type_id: addRelationForm.relation_type_id
    })
    if (res.code === 200) {
      message.success('创建成功')
      addRelationModalVisible.value = false
      fetchRelations()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '创建失败')
  } finally {
    addRelationLoading.value = false
  }
}

// 获取关系来源类型的颜色和文本
const getSourceTypeColor = (type: string) => {
  const colorMap: Record<string, string> = {
    'manual': 'blue',
    'reference': 'green',
    'rule': 'orange'
  }
  return colorMap[type] || 'default'
}

const getSourceTypeText = (type: string) => {
  const textMap: Record<string, string> = {
    'manual': '手动',
    'reference': '引用',
    'rule': '规则'
  }
  return textMap[type] || type
}

const deleteRelation = async (id: number) => {
  try {
    const res = await deleteRelationApi(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchRelations()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const filterCiOption = (input: string, option: any) => {
  return option.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
}

const openTopologyNodeDetail = async (instanceId?: number) => {
  const targetId = Number(instanceId || selectedTopologyNode.value?.id)
  if (!targetId) return
  if (targetId === getActiveInstanceId()) return

  currentInstanceId.value = targetId
  activeTab.value = 'basic'
  relationViewTab.value = 'list'
  await fetchDetail()
  await fetchHistory()
}

onMounted(() => {
  fetchRelationTypes()
})
</script>

<style scoped>
.attributes-empty {
  padding: 24px;
  text-align: center;
  color: #999;
}

.attributes-layout {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attributes-section-simple {
  border: 1px solid #eef3fb;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}

.attributes-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 10px;
}

.attribute-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-height: 34px;
}

.attribute-line-label {
  flex-shrink: 0;
  line-height: 34px;
  font-size: 13px;
  font-weight: 600;
  color: #262626;
}

.attribute-line-value-box {
  flex: 1;
  min-height: 34px;
  line-height: 34px;
  padding: 0 10px;
  border-radius: 6px;
  background: #eaf4ff;
  border: 1px solid #cfe3ff;
  font-size: 13px;
  color: #1d4e89;
  word-break: break-word;
}

.attribute-line-value-box :deep(.ant-image) {
  line-height: normal;
  vertical-align: middle;
}

.attribute-line-value-box :deep(.ant-btn-link) {
  padding-inline: 0;
}

.empty-value {
  color: #999;
}

.ci-graph-container {
  width: 100%;
  height: 400px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  background: #fafafa;
}

.topology-node-panel {
  margin-top: 12px;
}

.topology-node-actions {
  margin-top: 8px;
  text-align: right;
}
</style>
