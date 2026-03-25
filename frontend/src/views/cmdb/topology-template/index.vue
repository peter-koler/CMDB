<template>
  <div class="app-page template-list-page">
    <a-card :bordered="false" title="拓扑模板列表" class="app-surface-card">
      <template #extra>
        <a-space>
          <a-button @click="loadTemplates">刷新</a-button>
          <a-button type="primary" @click="createTemplate">新建模板</a-button>
        </a-space>
      </template>

      <a-table :columns="columns" :data-source="templates" row-key="id" :pagination="{ pageSize: 8 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'seed'">
            {{ record.seedModels.join(', ') || '-' }}
          </template>
          <template v-else-if="column.key === 'updatedAt'">
            {{ formatTime(record.updatedAt) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="editTemplate(record.id)">编辑</a-button>
              <a-button type="link" size="small" @click="copyTemplate(record.id)">复制</a-button>
              <a-popconfirm title="确认删除该模板？" @confirm="removeTemplate(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  cloneTopologyTemplate,
  deleteTopologyTemplate,
  listTopologyTemplates,
  TopologyTemplate
} from '@/mock/topology-template'

const router = useRouter()
const templates = ref<TopologyTemplate[]>([])

const columns = [
  { title: '模板名称', dataIndex: 'name', key: 'name' },
  { title: '说明', dataIndex: 'description', key: 'description' },
  { title: 'Seed 模型', key: 'seed', width: 220 },
  { title: '更新于', key: 'updatedAt', width: 190 },
  { title: '操作', key: 'action', width: 220 }
]

const loadTemplates = () => {
  templates.value = listTopologyTemplates()
}

const formatTime = (value: string) => {
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const createTemplate = () => {
  router.push('/cmdb/topology-template/edit/new')
}

const editTemplate = (id: string) => {
  router.push(`/cmdb/topology-template/edit/${id}`)
}

const copyTemplate = (id: string) => {
  const next = cloneTopologyTemplate(id)
  if (!next) {
    message.error('复制失败')
    return
  }
  message.success('模板已复制')
  loadTemplates()
}

const removeTemplate = (id: string) => {
  templates.value = deleteTopologyTemplate(id)
  message.success('模板已删除')
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.template-list-page {
  min-height: calc(100vh - 120px);
}
</style>
