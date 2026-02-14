<template>
  <div class="search-page">
    <a-card :bordered="false">
      <a-space direction="vertical" style="width: 100%" :size="16">
        <a-row :gutter="16">
          <a-col :xs="24" :sm="12" :md="8">
            <a-input-search
              v-model:value="searchKeyword"
              placeholder="搜索CI编码、名称或属性值"
              enter-button="搜索"
              size="large"
              @search="handleSearch"
            />
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-select
              v-model:value="searchModelId"
              placeholder="选择模型(可选)"
              allowClear
              style="width: 100%"
              @change="handleSearch"
            >
              <a-select-option v-for="model in modelList" :key="model.id" :value="model.id">
                {{ model.name }}
              </a-select-option>
            </a-select>
          </a-col>
          <a-col :xs="24" :sm="12" :md="6">
            <a-select
              v-model:value="searchDeptId"
              placeholder="选择部门(可选)"
              allowClear
              style="width: 100%"
              @change="handleSearch"
            >
              <a-select-option v-for="dept in deptList" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </a-select-option>
            </a-select>
          </a-col>
        </a-row>

        <a-alert
          v-if="searched"
          :message="`找到 ${totalCount} 条结果`"
          type="info"
          show-icon
        />

        <a-table
          :columns="columns"
          :data-source="searchResults"
          :loading="loading"
          :pagination="pagination"
          row-key="id"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'code'">
              <a @click="handleView(record)" style="color: #1890ff; cursor: pointer;">
                {{ record.code }}
              </a>
            </template>
            <template v-else-if="column.key === 'model'">
              {{ record.model_name }}
            </template>
            <template v-else-if="column.key === 'department'">
              {{ record.department_name }}
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDateTime(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="handleView(record)">查看</a-button>
                <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-space>
    </a-card>

    <CiDetailDrawer
      v-model:visible="detailDrawerVisible"
      :instance-id="currentInstanceId"
      @edit="handleEditFromDetail"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { searchInstances } from '@/api/ci'
import { getModelsTree } from '@/api/cmdb'
import { getDepartments } from '@/api/department'
import CiDetailDrawer from '@/views/cmdb/instance/components/CiDetailDrawer.vue'
import dayjs from 'dayjs'

const router = useRouter()

const searchKeyword = ref('')
const searchModelId = ref<number | null>(null)
const searchDeptId = ref<number | null>(null)
const searchResults = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)
const totalCount = ref(0)

const detailDrawerVisible = ref(false)
const currentInstanceId = ref<number | null>(null)

const modelList = ref<any[]>([])
const deptList = ref<any[]>([])

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0
})

const columns = [
  { title: 'CI编码', dataIndex: 'code', key: 'code', width: 180 },
  { title: 'CI名称', dataIndex: 'name', key: 'name' },
  { title: '模型', dataIndex: 'model_name', key: 'model', width: 120 },
  { title: '部门', dataIndex: 'department_name', key: 'department', width: 120 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' }
]

onMounted(() => {
  fetchModels()
  fetchDepartments()
})

const fetchModels = async () => {
  try {
    const res = await getModelsTree()
    if (res.code === 200) {
      const models: any[] = []
      const flattenModels = (items: any[]) => {
        items.forEach(item => {
          if (item.is_model) {
            models.push({ id: item.model_id, name: item.title || item.name })
          }
          if (item.children) {
            flattenModels(item.children)
          }
        })
      }
      flattenModels(res.data)
      modelList.value = models
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchDepartments = async () => {
  try {
    const res = await getDepartments()
    if (res.code === 200) {
      const depts: any[] = []
      const flattenDepts = (items: any[]) => {
        items.forEach(item => {
          depts.push({ id: item.id, name: item.name })
          if (item.children) {
            flattenDepts(item.children)
          }
        })
      }
      flattenDepts(res.data)
      deptList.value = depts
    }
  } catch (error) {
    console.error(error)
  }
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    message.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  searched.value = true

  try {
    const res = await searchInstances({
      keyword: searchKeyword.value,
      model_id: searchModelId.value,
      department_id: searchDeptId.value,
      page: pagination.value.current,
      per_page: pagination.value.pageSize
    })

    if (res.code === 200) {
      searchResults.value = res.data.items || []
      totalCount.value = res.data.total || 0
      pagination.value.total = res.data.total || 0
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  handleSearch()
}

const handleView = (record: any) => {
  currentInstanceId.value = record.id
  detailDrawerVisible.value = true
}

const handleEditFromDetail = (instance: any) => {
  router.push({
    path: '/cmdb/instance',
    query: { modelId: instance.model_id }
  })
}

const handleEdit = (record: any) => {
  router.push({
    path: '/cmdb/instance',
    query: { modelId: record.model_id }
  })
}

const formatDateTime = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}
</script>

<style scoped>
.search-page {
  padding: 16px;
}
</style>
