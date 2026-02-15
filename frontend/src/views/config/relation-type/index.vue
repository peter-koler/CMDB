<template>
  <div class="relation-type-page">
    <a-card :bordered="false" class="search-card">
      <a-form layout="inline" class="search-form">
        <a-row :gutter="[16, 16]" style="width: 100%">
          <a-col :xs="24" :sm="12" :md="8">
            <a-form-item label="关键词">
              <a-input
                v-model:value="searchKeyword"
                placeholder="请输入关系类型名称或编码"
                allowClear
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="24" :md="8">
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
                <a-button type="primary" @click="showModal()">
                  <template #icon><PlusOutlined /></template>
                  新增关系类型
                </a-button>
              </a-space>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card :bordered="false" class="table-card">
      <a-table
        :columns="columns"
        :data-source="relationTypes"
        :loading="loading"
        :pagination="pagination"
        @change="handleTableChange"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'direction'">
            <a-tag :color="record.direction === 'directed' ? 'blue' : 'green'">
              {{ record.direction === 'directed' ? '有向' : '双向' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'cardinality'">
            <a-tag>
              {{ getCardinalityText(record.cardinality) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'allow_self_loop'">
            <a-tag :color="record.allow_self_loop ? 'green' : 'red'">
              {{ record.allow_self_loop ? '允许' : '禁止' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'style'">
            <a-space size="small">
              <span
                style="display: inline-block; width: 14px; height: 14px; border-radius: 2px; border: 1px solid #d9d9d9;"
                :style="{ backgroundColor: record.style?.color || '#1890ff' }"
              />
              <span>{{ record.style?.lineType === 'dashed' ? '虚线' : '实线' }}</span>
            </a-space>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space wrap>
              <a-button type="link" size="small" @click="showModal(record)">
                编辑
              </a-button>
              <a-popconfirm
                title="确定删除该关系类型吗？"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" size="small" danger>
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑关系类型' : '新增关系类型'"
      width="700px"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
    >
      <a-form :model="form" :rules="rules" ref="formRef" :label-col="{ span: 5 }" :wrapper-col="{ span: 19 }">
        <a-form-item label="编码" name="code">
          <a-input v-model:value="form.code" placeholder="请输入编码" />
        </a-form-item>
        <a-form-item label="名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入名称" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="源端描述" name="source_label">
              <a-input v-model:value="form.source_label" placeholder="如：运行" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="目标端描述" name="target_label">
              <a-input v-model:value="form.target_label" placeholder="如：承载" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="方向" name="direction">
              <a-select v-model:value="form.direction" placeholder="请选择方向">
                <a-select-option value="directed">有向</a-select-option>
                <a-select-option value="bidirectional">双向</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="基数限制" name="cardinality">
              <a-select v-model:value="form.cardinality" placeholder="请选择基数限制">
                <a-select-option value="one_one">1:1</a-select-option>
                <a-select-option value="one_many">1:N</a-select-option>
                <a-select-option value="many_many">N:N</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="允许的源模型">
              <a-select
                v-model:value="form.source_model_ids"
                mode="multiple"
                placeholder="请选择允许的源模型"
                style="width: 100%"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="允许的目标模型">
              <a-select
                v-model:value="form.target_model_ids"
                mode="multiple"
                placeholder="请选择允许的目标模型"
                style="width: 100%"
              >
                <a-select-option v-for="model in models" :key="model.id" :value="model.id">
                  {{ model.name }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="允许自环">
          <a-switch v-model:checked="form.allow_self_loop" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
        <a-divider orientation="left">拓扑样式</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="连线颜色">
              <a-input v-model:value="form.style.color" type="color" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="线宽">
              <a-input-number v-model:value="form.style.lineWidth" :min="1" :max="10" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="线型">
              <a-select v-model:value="form.style.lineType" placeholder="请选择线型">
                <a-select-option value="solid">实线</a-select-option>
                <a-select-option value="dashed">虚线</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="箭头样式">
              <a-select v-model:value="form.style.arrow" placeholder="请选择箭头样式">
                <a-select-option value="default">默认</a-select-option>
                <a-select-option value="none">无箭头</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getRelationTypes, createRelationType, updateRelationType, deleteRelationType } from '@/api/cmdb-relation'
import { getModels } from '@/api/cmdb'

const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const searchKeyword = ref('')
const formRef = ref()

const relationTypes = ref<any[]>([])
const models = ref<any[]>([])

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '名称', dataIndex: 'name', key: 'name', width: 150 },
  { title: '源端描述', dataIndex: 'source_label', key: 'source_label', width: 120 },
  { title: '目标端描述', dataIndex: 'target_label', key: 'target_label', width: 120 },
  { title: '方向', dataIndex: 'direction', key: 'direction', width: 100 },
  { title: '基数限制', dataIndex: 'cardinality', key: 'cardinality', width: 100 },
  { title: '自环', dataIndex: 'allow_self_loop', key: 'allow_self_loop', width: 100 },
  { title: '样式', key: 'style', width: 120 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 150, fixed: 'right' as const }
]

const form = reactive({
  id: null as number | null,
  code: '',
  name: '',
  source_label: '',
  target_label: '',
  direction: 'directed',
  cardinality: 'many_many',
  source_model_ids: [] as number[],
  target_model_ids: [] as number[],
  allow_self_loop: false,
  description: '',
  style: {
    color: '#1890ff',
    lineWidth: 2,
    lineType: 'solid',
    arrow: 'default'
  }
})

const rules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

const getCardinalityText = (value: string) => {
  const map: Record<string, string> = {
    'one_one': '1:1',
    'one_many': '1:N',
    'many_many': 'N:N'
  }
  return map[value] || value
}

const fetchRelationTypes = async () => {
  loading.value = true
  try {
    const res = await getRelationTypes({
      page: pagination.current,
      per_page: pagination.pageSize,
      keyword: searchKeyword.value
    })
    if (res.code === 200) {
      relationTypes.value = res.data.items
      pagination.total = res.data.total
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

const showModal = (record?: any) => {
  isEdit.value = !!record
  if (record) {
    Object.assign(form, {
      id: record.id,
      code: record.code,
      name: record.name,
      source_label: record.source_label,
      target_label: record.target_label,
      direction: record.direction,
      cardinality: record.cardinality,
      source_model_ids: record.source_model_ids || [],
      target_model_ids: record.target_model_ids || [],
      allow_self_loop: record.allow_self_loop,
      description: record.description || '',
      style: {
        color: record.style?.color || '#1890ff',
        lineWidth: record.style?.lineWidth || 2,
        lineType: record.style?.lineType || 'solid',
        arrow: record.style?.arrow || 'default'
      }
    })
  } else {
    Object.assign(form, {
      id: null,
      code: '',
      name: '',
      source_label: '',
      target_label: '',
      direction: 'directed',
      cardinality: 'many_many',
      source_model_ids: [],
      target_model_ids: [],
      allow_self_loop: false,
      description: '',
      style: {
        color: '#1890ff',
        lineWidth: 2,
        lineType: 'solid',
        arrow: 'default'
      }
    })
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    let res
    if (isEdit.value) {
      res = await updateRelationType(form.id!, form)
    } else {
      res = await createRelationType(form)
    }
    if (res.code === 200) {
      message.success(isEdit.value ? '更新成功' : '创建成功')
      modalVisible.value = false
      fetchRelationTypes()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    const res = await deleteRelationType(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchRelationTypes()
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchRelationTypes()
}

const handleReset = () => {
  searchKeyword.value = ''
  pagination.current = 1
  fetchRelationTypes()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchRelationTypes()
}

onMounted(() => {
  fetchRelationTypes()
  fetchModels()
})
</script>

<style scoped>
.relation-type-page {
  padding: 16px;
}

.search-card {
  margin-bottom: 16px;
}

.search-form {
  width: 100%;
}

.table-card {
  margin-bottom: 16px;
}
</style>
