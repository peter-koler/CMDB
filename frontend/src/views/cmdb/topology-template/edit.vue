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
              <a-select
                v-model:value="form.seedModels"
                mode="multiple"
                :loading="baseOptionsLoading"
                placeholder="请选择 Seed 模型"
                allow-clear
              >
                <a-select-option v-for="item in modelOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="关系穿透方向">
              <a-radio-group v-model:value="form.traverseDirection" button-style="solid" size="small">
                <a-radio-button value="down">向下</a-radio-button>
                <a-radio-button value="up">向上</a-radio-button>
                <a-radio-button value="both">双向</a-radio-button>
              </a-radio-group>
            </a-form-item>

            <a-form-item label="允许关系类型">
              <a-checkbox-group v-model:value="form.allowedRelationTypes" :options="relationTypeOptionItems" />
            </a-form-item>

            <a-divider orientation="left">展开/收起资源类型（模型剪枝）</a-divider>
            <a-form-item label="可见模型（多选）">
              <a-select
                v-model:value="form.visibleModelKeys"
                mode="multiple"
                show-search
                option-filter-prop="label"
                :loading="baseOptionsLoading"
                placeholder="请选择可见模型（支持模糊搜索）"
                allow-clear
                :max-tag-count="4"
              >
                <a-select-option v-for="item in modelOptions" :key="item.value" :value="item.value" :label="item.label">
                  {{ item.label }}
                </a-select-option>
              </a-select>
            </a-form-item>

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
                  :loading="baseOptionsLoading"
                  style="width: 100%"
                  placeholder="选择归属模型"
                  allow-clear
                >
                  <a-select-option v-for="item in modelOptions" :key="item.value" :value="item.value">
                    {{ item.label }}
                  </a-select-option>
                </a-select>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import {
  createEmptyTemplate,
  modelDefs,
  relationTypeOptions
} from './utils/template-meta'
import { getModels, getModelsTree } from '@/api/cmdb'
import { getRelationTypes } from '@/api/cmdb-relation'
import {
  createCmdbTopologyTemplate,
  getCmdbTopologyTemplate,
  TopologyTemplate,
  updateCmdbTopologyTemplate
} from '@/api/cmdb-topology-template'

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id || 'new'))
const isNew = computed(() => id.value === 'new')

type OptionItem = { label: string; value: string }

const modelOptions = ref<OptionItem[]>(modelDefs.map((item) => ({ label: item.label, value: item.key })))
const relationTypeOptionItems = ref<OptionItem[]>(relationTypeOptions.map((item) => ({ label: item.label, value: item.value })))
const baseOptionsLoading = ref(false)

const modelByKey = computed<Record<string, { key: string; label: string }>>(() => {
  const map: Record<string, { key: string; label: string }> = {}
  modelOptions.value.forEach((item) => {
    map[item.value] = { key: item.value, label: item.label }
  })
  return map
})

const form = reactive<TopologyTemplate>(createEmptyTemplate())

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

const normalizeFormByOptions = () => {
  const validModelKeys = new Set(modelOptions.value.map((item) => item.value))
  form.seedModels = form.seedModels.filter((key) => validModelKeys.has(key))
  form.visibleModelKeys = form.visibleModelKeys.filter((key) => validModelKeys.has(key))
  form.layers = form.layers.map((layer) => ({
    ...layer,
    modelKeys: layer.modelKeys.filter((key) => validModelKeys.has(key))
  }))
  if (form.seedModels.length === 0 && modelOptions.value.length > 0) {
    form.seedModels = [modelOptions.value[0].value]
  }
  if (form.visibleModelKeys.length === 0) {
    form.visibleModelKeys = modelOptions.value.map((item) => item.value)
  }
}

const flattenModelTree = (tree: any[]): OptionItem[] => {
  const result: OptionItem[] = []
  const walk = (nodes: any[]) => {
    nodes.forEach((node) => {
      if (!node || typeof node !== 'object') return
      if (node.is_model && node.code) {
        result.push({
          value: String(node.code),
          label: String(node.title || node.name || node.code)
        })
      }
      if (Array.isArray(node.children)) {
        walk(node.children)
      }
    })
  }
  walk(tree || [])
  return result
}

const loadBaseOptions = async () => {
  baseOptionsLoading.value = true
  try {
    const [modelsTreeRes, relationTypesRes] = await Promise.all([
      getModelsTree(),
      getRelationTypes({ page: 1, per_page: 1000 })
    ])

    const modelItems = flattenModelTree(Array.isArray(modelsTreeRes?.data) ? modelsTreeRes.data : [])
    const relationItems = Array.isArray(relationTypesRes?.data?.items) ? relationTypesRes.data.items : []

    if (modelItems.length > 0) {
      modelOptions.value = modelItems
    }

    if (relationItems.length > 0) {
      relationTypeOptionItems.value = relationItems
        .map((item: any) => ({
          value: String(item?.code || item?.name || item?.id || ''),
          label: String(item?.name || item?.code || item?.id || '')
        }))
        .filter((item: OptionItem) => item.value && item.label)
    }
  } catch {
    // models/tree 失败时回退 models 列表接口，尽量保证可选
    try {
      const fallbackRes = await getModels({ page: 1, per_page: 1000 })
      const fallbackItems = Array.isArray(fallbackRes?.data?.items) ? fallbackRes.data.items : []
      if (fallbackItems.length > 0) {
        modelOptions.value = fallbackItems
          .map((item: any) => ({
            value: String(item?.code || ''),
            label: String(item?.name || item?.code || '')
          }))
          .filter((item: OptionItem) => item.value && item.label)
      }
    } catch {
      message.warning('模型或关系类型加载失败，已使用默认选项')
    }
  } finally {
    normalizeFormByOptions()
    baseOptionsLoading.value = false
  }
}

const loadTemplate = () => {
  if (isNew.value) {
    syncForm(createEmptyTemplate())
    normalizeFormByOptions()
    return
  }
  void (async () => {
    const res = await getCmdbTopologyTemplate(id.value)
    if (res.code !== 200 || !res.data) {
      message.error('模板不存在')
      router.push('/cmdb/topology-template')
      return
    }
    syncForm(res.data)
    normalizeFormByOptions()
  })()
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

const saveTemplate = async () => {
  if (!form.name.trim()) {
    message.warning('请输入模板名称')
    return
  }
  if (form.seedModels.length === 0) {
    message.warning('请至少选择一个 Seed 模型')
    return
  }
  const payload = { ...form }
  const res = isNew.value
    ? await createCmdbTopologyTemplate(payload)
    : await updateCmdbTopologyTemplate(form.id, payload)
  if (res.code !== 200) {
    message.error(res.message || '模板保存失败')
    return
  }
  if (res.data?.id) {
    form.id = res.data.id
  }
  message.success(isNew.value ? '模板创建成功' : '模板保存成功')
  router.push('/cmdb/topology-template')
}

const previewTopology = async () => {
  if (!form.name.trim()) {
    message.warning('请先输入模板名称')
    return
  }
  if (isNew.value) {
    const created = await createCmdbTopologyTemplate({ ...form })
    if (created.code !== 200 || !created.data?.id) {
      message.error(created.message || '保存模板失败，无法预览')
      return
    }
    form.id = created.data.id
  } else {
    const updated = await updateCmdbTopologyTemplate(form.id, { ...form })
    if (updated.code !== 200) {
      message.error(updated.message || '保存模板失败，无法预览')
      return
    }
  }
  router.push(`/cmdb/topology-manage?templateId=${form.id}`)
}

const goBack = () => {
  router.push('/cmdb/topology-template')
}

onMounted(() => {
  void (async () => {
    await loadBaseOptions()
    loadTemplate()
  })()
})

watch(
  () => form.seedModels,
  () => {
    normalizeFormByOptions()
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
