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
        <a-popconfirm
          title="确定要删除此CI吗？"
          ok-text="确定"
          cancel-text="取消"
          @confirm="handleDelete"
        >
          <a-button danger>删除</a-button>
        </a-popconfirm>
      </a-space>
    </template>

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
        <div v-if="modelFields.length === 0" style="padding: 20px; text-align: center; color: #999;">
          暂无属性信息
        </div>
        <div v-else class="attributes-form">
          <a-row :gutter="[16, 16]">
            <a-col
              v-for="field in modelFields"
              :key="field.code"
              :span="field.span || 12"
            >
              <div class="field-item">
                <span class="field-label">{{ field.name }}：</span>
                <span class="field-value">
                  <template v-if="field.field_type === 'boolean'">
                    <a-tag :color="attributeValues[field.code] ? 'green' : 'red'">
                      {{ attributeValues[field.code] ? '是' : '否' }}
                    </a-tag>
                  </template>
                  <template v-else-if="field.field_type === 'image'">
                    <a-image
                      v-if="attributeValues[field.code]"
                      :src="attributeValues[field.code]"
                      :width="100"
                    />
                    <span v-else class="empty-value">-</span>
                  </template>
                  <template v-else-if="field.field_type === 'file'">
                    <a-button
                      v-if="attributeValues[field.code]"
                      type="link"
                      size="small"
                      @click="downloadFile(attributeValues[field.code])"
                    >
                      下载文件
                    </a-button>
                    <span v-else class="empty-value">-</span>
                  </template>
                  <template v-else-if="field.field_type === 'date'">
                    {{ attributeValues[field.code] ? formatDate(attributeValues[field.code]) : '-' }}
                  </template>
                  <template v-else-if="field.field_type === 'datetime'">
                    {{ attributeValues[field.code] ? formatDateTime(attributeValues[field.code]) : '-' }}
                  </template>
                  <template v-else-if="field.field_type === 'number'">
                    {{ attributeValues[field.code] ?? '-' }}
                  </template>
                  <template v-else>
                    {{ attributeValues[field.code] || '-' }}
                  </template>
                </span>
              </div>
            </a-col>
          </a-row>
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
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="依赖的" :bordered="false">
                  <a-table
                    :columns="outRelationColumns"
                    :data-source="outRelations"
                    :loading="relationsLoading"
                    :pagination="false"
                    row-key="id"
                    size="small"
                  >
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'action'">
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
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="被依赖的" :bordered="false">
                  <a-table
                    :columns="inRelationColumns"
                    :data-source="inRelations"
                    :loading="relationsLoading"
                    :pagination="false"
                    row-key="id"
                    size="small"
                  >
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'action'">
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
                </a-card>
              </a-col>
            </a-row>
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
import { ref, watch, computed, onMounted, reactive, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { getInstanceDetail, getCiHistory, deleteInstance, getInstances } from '@/api/ci'
import { getInstanceRelations, createRelation, deleteRelation as deleteRelationApi, getRelationTypes } from '@/api/cmdb-relation'
import { PlusOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'

interface Props {
  visible: boolean
  instanceId: number | null
}

const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'edit', 'deleted'])

const activeTab = ref('basic')
const ciData = ref<any>(null)
const modelFields = ref<any[]>([])
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

const outRelationColumns = [
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name' },
  { title: '目标CI', dataIndex: 'target_ci_name', key: 'target_ci_name' },
  { title: '编码', dataIndex: 'target_ci_code', key: 'target_ci_code', width: 120 },
  { title: '模型', dataIndex: 'target_ci_model_name', key: 'target_ci_model_name', width: 100 },
  { title: '来源', dataIndex: 'source_type', key: 'source_type', width: 80 },
  { title: '操作', key: 'action', width: 80 }
]

const inRelationColumns = [
  { title: '关系类型', dataIndex: 'relation_type_name', key: 'relation_type_name' },
  { title: '源CI', dataIndex: 'source_ci_name', key: 'source_ci_name' },
  { title: '编码', dataIndex: 'source_ci_code', key: 'source_ci_code', width: 120 },
  { title: '模型', dataIndex: 'source_ci_model_name', key: 'source_ci_model_name', width: 100 },
  { title: '来源', dataIndex: 'source_type', key: 'source_type', width: 80 },
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
    return ciData.value?.attribute_values || {}
  } catch {
    return {}
  }
})

watch(() => props.instanceId, async (val) => {
  if (val && props.visible) {
    await fetchDetail()
    await fetchHistory()
  }
})

watch(() => props.visible, (val) => {
  if (val) {
    activeTab.value = 'basic'
    historyPagination.value = { current: 1, pageSize: 10, total: 0 }
  }
})

const fetchDetail = async () => {
  if (!props.instanceId) return

  loading.value = true
  try {
    const res = await getInstanceDetail(props.instanceId)
    
    if (res.code === 200) {
      ciData.value = res.data
      const formConfig = res.data.model?.form_config
      if (formConfig) {
        try {
          let parsed = formConfig
          if (typeof parsed === 'string') {
            parsed = JSON.parse(parsed)
          }
          if (typeof parsed === 'string') {
            parsed = JSON.parse(parsed)
          }
          
          modelFields.value = parsed.map((item: any, index: number) => ({
            id: item.id || `field_${index}`,
            code: item.props?.code || item.id,
            name: item.props?.label || item.props?.code || '',
            field_type: mapControlTypeToFieldType(item.controlType),
            span: item.props?.span || 12,
            placeholder: item.props?.placeholder || '',
            required: item.props?.required || false
          }))
        } catch (e) {
          console.error('解析form_config失败:', e)
          modelFields.value = []
        }
      } else {
        modelFields.value = res.data.model?.fields || []
      }
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchHistory = async () => {
  if (!props.instanceId) return

  historyLoading.value = true
  try {
    const res = await getCiHistory(props.instanceId)
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

const handleDelete = async () => {
  if (!props.instanceId) return
  
  try {
    const res = await deleteInstance(props.instanceId)
    if (res.code === 200) {
      message.success('删除成功')
      emit('deleted')
      handleClose()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
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
    'file': 'file'
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
  if (val === 'history' && props.instanceId) {
    fetchHistory()
  }
  if (val === 'relations' && props.instanceId) {
    fetchRelations()
  }
})

const fetchRelations = async () => {
  if (!props.instanceId) return
  relationsLoading.value = true
  try {
    const res = await getInstanceRelations(props.instanceId, { depth: relationDepth.value })
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
  try {
    const res = await getInstances({ per_page: 1000 })
    if (res.code === 200) {
      candidateCis.value = res.data.items.filter((ci: any) => ci.id !== props.instanceId)
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
  if (!addRelationForm.relation_type_id || !addRelationForm.target_ci_id) {
    message.warning('请填写完整信息')
    return
  }

  addRelationLoading.value = true
  try {
    const res = await createRelation({
      source_ci_id: props.instanceId,
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

onMounted(() => {
  fetchRelationTypes()
})
</script>

<style scoped>
.attributes-form {
  padding: 8px 0;
}

.field-item {
  background: #fafafa;
  border-radius: 4px;
  padding: 12px 16px;
  height: 100%;
  border: 1px solid #e8e8e8;
}

.field-label {
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

.field-value {
  color: #666;
  font-size: 14px;
}

.empty-value {
  color: #999;
}
</style>
