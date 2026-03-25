<template>
  <div class="app-page template-edit-page">
    <a-card :bordered="false" class="app-surface-card" :title="isNew ? '新建拓扑模板' : '编辑拓扑模板'">
      <template #extra>
        <a-space>
          <a-button @click="goBack">返回</a-button>
          <a-button @click="previewTopology">预览拓扑</a-button>
          <a-button type="primary" @click="saveTemplate">保存模板</a-button>
        </a-space>
      </template>

      <a-row :gutter="16">
        <a-col :xs="24" :xl="14">
          <a-form layout="vertical">
            <a-form-item label="模板名称" required>
              <a-input v-model:value="form.name" placeholder="请输入模板名称" />
            </a-form-item>
            <a-form-item label="模板说明">
              <a-textarea v-model:value="form.description" :rows="2" placeholder="请输入模板说明" />
            </a-form-item>

            <a-divider orientation="left">入口节点锚定</a-divider>
            <a-form-item label="Seed 模型（可多选）">
              <a-select v-model:value="form.seedModels" mode="multiple" :options="modelOptions" />
            </a-form-item>

            <a-form-item label="关系穿透方向">
              <a-radio-group v-model:value="form.traverseDirection" button-style="solid" size="small">
                <a-radio-button value="down">向下</a-radio-button>
                <a-radio-button value="up">向上</a-radio-button>
                <a-radio-button value="both">双向</a-radio-button>
              </a-radio-group>
            </a-form-item>

            <a-form-item label="允许关系类型">
              <a-checkbox-group v-model:value="form.allowedRelationTypes" :options="relationTypeOptions" />
            </a-form-item>

            <a-divider orientation="left">展开/收起资源类型（模型剪枝）</a-divider>
            <a-tree
              checkable
              block-node
              default-expand-all
              :tree-data="modelTreeData"
              :checked-keys="safeCheckedModelKeys"
              @check="handleModelTreeCheck"
            />

            <a-divider orientation="left">拓扑分层（Layout Mapping）</a-divider>
            <a-space direction="vertical" style="width: 100%" size="small">
              <div v-for="(layer, index) in form.layers" :key="layer.id" class="layer-item">
                <div class="layer-head">
                  <a-input v-model:value="layer.name" size="small" placeholder="层级名称" />
                  <a-space>
                    <a-button size="small" :disabled="index === 0" @click="moveLayer(index, -1)">上移</a-button>
                    <a-button size="small" :disabled="index === form.layers.length - 1" @click="moveLayer(index, 1)">下移</a-button>
                    <a-button size="small" danger @click="removeLayer(index)">删除</a-button>
                  </a-space>
                </div>
                <a-select
                  v-model:value="layer.modelKeys"
                  mode="multiple"
                  size="small"
                  :options="modelOptions"
                  placeholder="选择归属模型"
                />
              </div>
            </a-space>

            <a-space style="margin-top: 8px" wrap>
              <a-button size="small" @click="addLayer">新增层级</a-button>
              <a-select v-model:value="form.layoutDirection" size="small" style="width: 120px">
                <a-select-option value="horizontal">水平分层</a-select-option>
                <a-select-option value="vertical">垂直分层</a-select-option>
              </a-select>
            </a-space>

            <a-divider orientation="left">拓扑分组/聚合</a-divider>
            <a-form-item label="分组属性">
              <a-select v-model:value="form.groupBy" style="width: 180px">
                <a-select-option value="idc">按机房 (idc)</a-select-option>
                <a-select-option value="subnet">按子网 (subnet)</a-select-option>
                <a-select-option value="owner">按负责人 (owner)</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item>
              <a-checkbox v-model:checked="form.aggregateEnabled">启用智能聚合</a-checkbox>
            </a-form-item>

            <a-form-item label="数量触发阈值 N">
              <a-input-number v-model:value="form.aggregateThreshold" :min="2" :max="20" />
            </a-form-item>
          </a-form>
        </a-col>

        <a-col :xs="24" :xl="10">
          <a-card size="small" class="app-surface-card" title="模板摘要">
            <a-descriptions :column="1" size="small" bordered>
              <a-descriptions-item label="名称">{{ form.name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="Seed">{{ form.seedModels.join(', ') || '-' }}</a-descriptions-item>
              <a-descriptions-item label="关系类型">{{ form.allowedRelationTypes.join(', ') || '-' }}</a-descriptions-item>
              <a-descriptions-item label="可见模型">{{ form.visibleModelKeys.length }}</a-descriptions-item>
              <a-descriptions-item label="层级数">{{ form.layers.length }}</a-descriptions-item>
              <a-descriptions-item label="分组键">{{ form.groupBy }}</a-descriptions-item>
              <a-descriptions-item label="聚合阈值">{{ form.aggregateEnabled ? form.aggregateThreshold : '关闭' }}</a-descriptions-item>
            </a-descriptions>
          </a-card>

          <a-card size="small" class="app-surface-card" title="层级定义" style="margin-top: 12px">
            <a-timeline>
              <a-timeline-item v-for="layer in form.layers" :key="layer.id">
                <b>{{ layer.name || '未命名层' }}</b>
                <div class="timeline-desc">{{ layer.modelKeys.map(getModelLabel).join(' / ') || '未配置模型' }}</div>
              </a-timeline-item>
            </a-timeline>
          </a-card>
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import {
  buildModelTree,
  createEmptyTemplate,
  getTopologyTemplate,
  modelDefs,
  relationTypeOptions,
  TopologyTemplate,
  upsertTopologyTemplate
} from '@/mock/topology-template'

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id || 'new'))
const isNew = computed(() => id.value === 'new')

const modelByKey = computed<Record<string, { key: string; label: string }>>(() => {
  const map: Record<string, { key: string; label: string }> = {}
  modelDefs.forEach((item) => {
    map[item.key] = item
  })
  return map
})

const modelOptions = modelDefs.map((item) => ({ label: item.label, value: item.key }))

const form = reactive<TopologyTemplate>(createEmptyTemplate())

const modelTreeData = computed(() => buildModelTree(form.seedModels, modelByKey.value))

const collectTreeKeys = (nodes: any[]): string[] => {
  return nodes.flatMap((node) => [
    String(node.key),
    ...(Array.isArray(node.children) ? collectTreeKeys(node.children) : [])
  ])
}

const treeModelKeySet = computed(() => new Set(collectTreeKeys(modelTreeData.value)))
const safeCheckedModelKeys = computed(() => form.visibleModelKeys.filter((key) => treeModelKeySet.value.has(key)))

const sanitizeVisibleModelKeys = () => {
  const sanitized = form.visibleModelKeys.filter((key) => treeModelKeySet.value.has(key))
  if (sanitized.length !== form.visibleModelKeys.length) {
    form.visibleModelKeys = sanitized
  }
}

const getModelLabel = (modelKey: string) => modelByKey.value[modelKey]?.label || modelKey

const syncForm = (target: TopologyTemplate) => {
  form.id = target.id
  form.name = target.name
  form.description = target.description
  form.seedModels = [...target.seedModels]
  form.traverseDirection = target.traverseDirection
  form.allowedRelationTypes = [...target.allowedRelationTypes]
  form.visibleModelKeys = [...target.visibleModelKeys]
  form.layers = target.layers.map((layer) => ({ ...layer, modelKeys: [...layer.modelKeys] }))
  form.layoutDirection = target.layoutDirection
  form.groupBy = target.groupBy
  form.aggregateEnabled = target.aggregateEnabled
  form.aggregateThreshold = target.aggregateThreshold
  form.updatedAt = target.updatedAt
}

const loadTemplate = () => {
  if (isNew.value) {
    syncForm(createEmptyTemplate())
    return
  }
  const current = getTopologyTemplate(id.value)
  if (!current) {
    message.error('模板不存在')
    router.push('/cmdb/topology-template')
    return
  }
  syncForm(current)
  sanitizeVisibleModelKeys()
}

const handleModelTreeCheck = (checked: any) => {
  const keys = Array.isArray(checked) ? checked : checked?.checked
  form.visibleModelKeys = ((keys || []) as string[]).filter((key) => treeModelKeySet.value.has(key))
}

const moveLayer = (index: number, delta: number) => {
  const target = index + delta
  if (target < 0 || target >= form.layers.length) return
  const next = [...form.layers]
  const temp = next[index]
  next[index] = next[target]
  next[target] = temp
  form.layers = next
}

const removeLayer = (index: number) => {
  form.layers = form.layers.filter((_, i) => i !== index)
}

const addLayer = () => {
  form.layers = [
    ...form.layers,
    {
      id: `layer-${Date.now()}`,
      name: `新层级${form.layers.length + 1}`,
      modelKeys: []
    }
  ]
}

const saveTemplate = () => {
  if (!form.name.trim()) {
    message.warning('请输入模板名称')
    return
  }
  if (form.seedModels.length === 0) {
    message.warning('请至少选择一个 Seed 模型')
    return
  }
  upsertTopologyTemplate({ ...form })
  message.success('模板保存成功')
  router.push('/cmdb/topology-template')
}

const previewTopology = () => {
  upsertTopologyTemplate({ ...form })
  router.push(`/cmdb/topology-manage?templateId=${form.id}`)
}

const goBack = () => {
  router.push('/cmdb/topology-template')
}

onMounted(() => {
  loadTemplate()
})

watch(
  treeModelKeySet,
  () => {
    sanitizeVisibleModelKeys()
  },
  { immediate: true }
)

watch(
  () => form.seedModels,
  () => {
    sanitizeVisibleModelKeys()
  },
  { deep: true, flush: 'sync' }
)
</script>

<style scoped>
.template-edit-page {
  min-height: calc(100vh - 120px);
}

.layer-item {
  border: 1px solid var(--app-border);
  border-radius: 8px;
  padding: 8px;
  background: var(--app-surface-subtle);
}

.layer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.timeline-desc {
  color: var(--app-text-muted);
  font-size: 12px;
}
</style>
