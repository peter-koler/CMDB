<template>
  <div class="view-designer-page">
    <a-card :bordered="false" :body-style="{ padding: '16px' }">
      <div class="designer-header">
        <a-page-header :title="viewInfo.name" :sub-title="viewInfo.code" @back="goBack">
          <template #extra>
            <a-button @click="handleSave">保存</a-button>
          </template>
        </a-page-header>
      </div>

      <a-layout class="designer-layout">
        <a-layout-sider width="350" class="tree-sider">
          <div class="tree-header">
            <a-space>
              <a-button type="primary" size="small" @click="showAddRootNodeModal">
                <PlusOutlined />
                添加根节点
              </a-button>
              <a-button size="small" @click="expandAll">
                展开全部
              </a-button>
              <a-button size="small" @click="collapseAll">
                收起全部
              </a-button>
            </a-space>
          </div>
          <div class="tree-content">
            <a-tree
              v-if="treeData.length > 0"
              :tree-data="treeData"
              :expanded-keys="expandedKeys"
              :auto-expand-parent="autoExpandParent"
              :draggable="true"
              @drop="onDrop"
              @expand="onExpand"
              @select="onSelect"
            >
              <template #title="{ title, key, data }">
                <div class="tree-node-title" @dblclick="handleEditNode(key)">
                  <span>{{ title }}</span>
                  <a-space class="node-actions" size="small">
                    <a-button type="text" size="small" @click.stop="showAddChildModal(key)">
                      <PlusOutlined />
                    </a-button>
                    <a-button type="text" size="small" @click.stop="handleEditNode(key)">
                      <EditOutlined />
                    </a-button>
                    <a-popconfirm
                      title="确定删除该节点吗？"
                      @confirm="handleDeleteNode(key)"
                    >
                      <a-button type="text" size="small" danger @click.stop>
                        <DeleteOutlined />
                      </a-button>
                    </a-popconfirm>
                  </a-space>
                </div>
              </template>
            </a-tree>
            <a-empty v-else description="暂无节点，请添加根节点" />
          </div>
        </a-layout-sider>

        <a-layout-content class="config-content">
          <div v-if="selectedNode" class="node-config">
            <a-page-header :title="`配置节点: ${selectedNode.name}`">
              <template #extra>
                <a-button type="primary" @click="handleSaveNodeConfig">
                  保存配置
                </a-button>
              </template>
            </a-page-header>

            <a-tabs v-model:activeKey="configTab">
              <a-tab-pane key="basic" tab="基本信息">
                <a-form :model="nodeConfig" :label-col="{ span: 4 }">
                  <a-form-item label="节点名称">
                    <a-input v-model:value="nodeConfig.name" />
                  </a-form-item>
                  <a-form-item label="排序">
                    <a-input-number v-model:value="nodeConfig.sort_order" :min="0" />
                  </a-form-item>
                  <a-form-item label="状态">
                    <a-switch v-model:checked="nodeConfig.is_active" checked-children="启用" un-checked-children="禁用" />
                  </a-form-item>
                </a-form>
              </a-tab-pane>

              <a-tab-pane key="filter" tab="筛选配置" :disabled="selectedNode.is_root">
                <div v-if="selectedNode.is_root" class="tip-box">
                  <a-alert type="info" message="根节点不能设置筛选条件" show-icon />
                </div>
                <div v-else>
                  <a-space direction="vertical" style="width: 100%">
                    <a-form-item label="选择模型">
                      <a-select
                        v-model:value="nodeConfig.filter_config.model_id"
                        placeholder="请选择模型"
                        style="width: 300px"
                        @change="(val: number | string) => handleModelChange(val)"
                      >
                        <a-select-option v-for="model in cmdbModels" :key="model.id" :value="model.id">
                          {{ model.name }}
                        </a-select-option>
                      </a-select>
                    </a-form-item>

                    <a-divider>筛选条件</a-divider>

                    <a-alert
                      v-if="nodeConfig.filter_config.model_id && modelFields.length === 0"
                      type="warning"
                      message="该模型没有配置字段，请先在模型管理中配置表单字段"
                      show-icon
                      style="margin-bottom: 16px"
                    />

                    <div v-for="(condition, index) in nodeConfig.filter_config.conditions" :key="index" class="condition-item">
                      <a-space>
                        <a-select v-model:value="condition.field" placeholder="字段" style="width: 150px">
                          <a-select-option v-for="field in modelFields" :key="field.code" :value="field.code">
                            {{ field.name }}
                          </a-select-option>
                        </a-select>
                        <a-select v-model:value="condition.operator" placeholder="运算符" style="width: 100px">
                          <a-select-option value="eq">等于</a-select-option>
                          <a-select-option value="ne">不等于</a-select-option>
                          <a-select-option value="contains">包含</a-select-option>
                          <a-select-option value="gt">大于</a-select-option>
                          <a-select-option value="gte">大于等于</a-select-option>
                          <a-select-option value="lt">小于</a-select-option>
                          <a-select-option value="lte">小于等于</a-select-option>
                        </a-select>
                        <a-input v-model:value="condition.value" placeholder="值" style="width: 150px" />
                        <a-button type="text" danger @click="removeCondition(index as number)">
                          <DeleteOutlined />
                        </a-button>
                      </a-space>
                    </div>

                    <a-button type="dashed" @click="addCondition" style="width: 100%">
                      <PlusOutlined />
                      添加条件
                    </a-button>
                  </a-space>
                </div>
              </a-tab-pane>

              <a-tab-pane key="permission" tab="权限配置">
                <div class="permission-config">
                  <a-space style="margin-bottom: 16px">
                    <a-button type="primary" size="small" @click="showGrantPermissionModal">
                      授予权限
                    </a-button>
                  </a-space>
                  <a-table
                    :columns="permissionColumns"
                    :data-source="nodePermissions"
                    :pagination="false"
                    row-key="id"
                  >
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'action'">
                        <a-popconfirm
                          title="确定撤销该权限吗？"
                          @confirm="handleRevokePermission(record.role_id)"
                        >
                          <a-button type="link" size="small" danger>撤销</a-button>
                        </a-popconfirm>
                      </template>
                    </template>
                  </a-table>
                </div>
              </a-tab-pane>
            </a-tabs>
          </div>
          <a-empty v-else description="请选择左侧节点进行配置" />
        </a-layout-content>
      </a-layout>
    </a-card>

    <a-modal
      v-model:open="nodeModalVisible"
      :title="isEditNode ? '编辑节点' : (isAddChild ? '添加子节点' : '添加根节点')"
      @ok="handleNodeSubmit"
    >
      <a-form :model="nodeForm" :rules="nodeRules" ref="nodeFormRef">
        <a-form-item label="节点名称" name="name">
          <a-input v-model:value="nodeForm.name" placeholder="请输入节点名称" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="nodeForm.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="permissionModalVisible"
      title="授予权限"
      @ok="handleGrantPermission"
    >
      <a-form :model="permissionForm" :label-col="{ span: 4 }">
        <a-form-item label="选择角色">
          <a-select v-model:value="permissionForm.role_id" placeholder="请选择角色">
            <a-select-option v-for="role in allRoles" :key="role.id" :value="role.id">
              {{ role.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import {
  getCustomView,
  getViewNodes,
  createNode,
  updateNode,
  deleteNode,
  moveNode,
  getNodePermissions,
  grantNodePermission,
  revokeNodePermission
} from '@/api/custom-view'
import { getModels, getModelDetail } from '@/api/cmdb'
import { getRoles } from '@/api/role'

const route = useRoute()
const router = useRouter()

const viewId = computed(() => Number(route.params.id))
const viewInfo = ref<any>({})
const treeData = ref<any[]>([])
const expandedKeys = ref<number[]>([])
const autoExpandParent = ref(true)
const selectedNode = ref<any>(null)

const nodeModalVisible = ref(false)
const isEditNode = ref(false)
const isAddChild = ref(false)
const nodeFormRef = ref()
const nodeForm = reactive({
  id: null as number | null,
  parent_id: null as number | null,
  name: '',
  sort_order: 0
})
const nodeRules = {
  name: [{ required: true, message: '请输入节点名称' }]
}

const configTab = ref('basic')
const nodeConfig = reactive<any>({
  name: '',
  sort_order: 0,
  is_active: true,
  filter_config: {
    model_id: null,
    conditions: []
  }
})

const cmdbModels = ref<any[]>([])
const modelFields = ref<any[]>([])

const permissionColumns = [
  { title: '角色名称', dataIndex: 'role_name', key: 'role_name' },
  { title: '授权时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 100 }
]
const nodePermissions = ref<any[]>([])

const permissionModalVisible = ref(false)
const allRoles = ref<any[]>([])
const permissionForm = reactive({
  role_id: null as number | null
})

onMounted(async () => {
  await fetchViewInfo()
  await fetchTreeData()
  await fetchModels()
  await fetchRoles()
})

const fetchViewInfo = async () => {
  try {
    const res = await getCustomView(viewId.value)
    if (res.code === 200) {
      viewInfo.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchTreeData = async () => {
  try {
    const res = await getViewNodes(viewId.value)
    if (res.code === 200) {
      treeData.value = convertToTreeData(res.data)
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchModels = async () => {
  try {
    const res = await getModels({ per_page: 1000 })
    if (res.code === 200) {
      cmdbModels.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchRoles = async () => {
  try {
    const res = await getRoles({ per_page: 1000 })
    if (res.code === 200) {
      allRoles.value = res.data.items
    }
  } catch (error) {
    console.error(error)
  }
}

const convertToTreeData = (nodes: any[]): any[] => {
  return nodes.map(node => ({
    key: node.id,
    title: node.name,
    data: node,
    children: node.children ? convertToTreeData(node.children) : [],
    is_root: node.is_root,
    isLeaf: !node.children || node.children.length === 0
  }))
}

const onLoadData = (treeNode: any) => {
  return new Promise<void>((resolve) => {
    if (treeNode.children && treeNode.children.length > 0) {
      resolve()
      return
    }
    resolve()
  })
}

const onExpand = (keys: number[]) => {
  expandedKeys.value = keys
  autoExpandParent.value = false
}

const expandAll = () => {
  const keys: number[] = []
  const getKeys = (nodes: any[]) => {
    nodes.forEach(node => {
      keys.push(node.key)
      if (node.children) {
        getKeys(node.children)
      }
    })
  }
  getKeys(treeData.value)
  expandedKeys.value = keys
}

const collapseAll = () => {
  expandedKeys.value = []
}

const onSelect = async (selectedKeys: number[]) => {
  if (selectedKeys.length > 0) {
    const findNode = (nodes: any[]): any => {
      for (const node of nodes) {
        if (node.key === selectedKeys[0]) return node.data
        if (node.children) {
          const found = findNode(node.children)
          if (found) return found
        }
      }
      return null
    }
    selectedNode.value = findNode(treeData.value)
    if (selectedNode.value) {
      nodeConfig.name = selectedNode.value.name
      nodeConfig.sort_order = selectedNode.value.sort_order
      nodeConfig.is_active = selectedNode.value.is_active
      nodeConfig.filter_config = selectedNode.value.filter_config || { model_id: null, conditions: [] }
      if (!nodeConfig.filter_config.model_id) {
        nodeConfig.filter_config.model_id = null
      }
      if (!nodeConfig.filter_config.conditions) {
        nodeConfig.filter_config.conditions = []
      }
      await fetchNodePermissions(selectedNode.value.id)
    }
    if (nodeConfig.filter_config.model_id) {
      handleModelChange(nodeConfig.filter_config.model_id as number | string)
    }
  } else {
    selectedNode.value = null
  }
}

const fetchNodePermissions = async (nodeId: number) => {
  try {
    const res = await getNodePermissions(nodeId)
    if (res.code === 200) {
      nodePermissions.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const showAddRootNodeModal = () => {
  isEditNode.value = false
  isAddChild.value = false
  nodeForm.parent_id = null
  nodeForm.name = ''
  nodeForm.sort_order = 0
  nodeModalVisible.value = true
}

const findNodeByKey = (nodes: any[], key: number | string): any => {
  for (const node of nodes) {
    if (node.key === key) return node
    if (node.children && node.children.length > 0) {
      const found = findNodeByKey(node.children, key)
      if (found) return found
    }
  }
  return null
}

const showAddChildModal = (key: number | string) => {
  isEditNode.value = false
  isAddChild.value = true
  nodeForm.parent_id = Number(key)
  nodeForm.name = ''
  nodeForm.sort_order = 0
  nodeModalVisible.value = true
}

const handleEditNode = (key: number | string) => {
  const node = findNodeByKey(treeData.value, key)
  if (!node) return
  
  isEditNode.value = true
  isAddChild.value = false
  nodeForm.id = Number(key)
  nodeForm.parent_id = node.data.parent_id
  nodeForm.name = node.title
  nodeForm.sort_order = node.data.sort_order
  nodeModalVisible.value = true
}

const handleNodeSubmit = async () => {
  try {
    await nodeFormRef.value.validate()
    
    const submitData = {
      view_id: viewId.value,
      parent_id: nodeForm.parent_id,
      name: nodeForm.name,
      sort_order: nodeForm.sort_order
    }
    
    if (isEditNode.value) {
      await updateNode(nodeForm.id!, submitData)
      message.success('更新成功')
    } else {
      await createNode(submitData)
      message.success('创建成功')
    }
    
    nodeModalVisible.value = false
    await fetchTreeData()
    if (selectedNode.value) {
      onSelect([selectedNode.value.id])
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const handleDeleteNode = async (key: number) => {
  try {
    await deleteNode(key)
    message.success('删除成功')
    await fetchTreeData()
    if (selectedNode.value && selectedNode.value.id === key) {
      selectedNode.value = null
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const onDrop = async (info: any) => {
  const dropKey = info.node.key
  const dragKey = info.dragNode.key
  const dropPos = info.node.pos.split('-')
  const dropPosition = info.dropPosition - Number(dropPos[dropPos.length - 1])

  const findNode = (nodes: any[], key: number): any => {
    for (const node of nodes) {
      if (node.key === key) return node
      if (node.children) {
        const found = findNode(node.children, key)
        if (found) return found
      }
    }
    return null
  }

  const dragObj = findNode(treeData.value, dragKey)
  
  let newParentId = null
  if (info.dropToGap) {
    newParentId = info.node.parentNode?.key || null
  } else {
    newParentId = info.node.key
  }

  try {
    await moveNode(dragKey, {
      parent_id: newParentId,
      sort_order: 0
    })
    message.success('移动成功')
    await fetchTreeData()
  } catch (error: any) {
    message.error(error.response?.data?.message || '移动失败')
  }
}

const handleModelChange = async (modelId: number | string) => {
  modelFields.value = []
  const modelIdNum = Number(modelId)
  
  try {
    // 获取模型详情以获取 form_config
    const res = await getModelDetail(modelIdNum)
    if (res.code === 200 && res.data.form_config) {
      let formConfig = res.data.form_config
      // form_config 可能是字符串需要解析
      if (typeof formConfig === 'string') {
        try {
          formConfig = JSON.parse(formConfig)
        } catch (e) {
          formConfig = []
        }
      }
      if (typeof formConfig === 'string') {
        try {
          formConfig = JSON.parse(formConfig)
        } catch (e) {
          formConfig = []
        }
      }
      const configArray = Array.isArray(formConfig) ? formConfig : []
      
      // 递归提取字段
      const extractFields = (items: any[]): any[] => {
        const fields: any[] = []
        for (const item of items) {
          if (!item || typeof item !== 'object') continue
          
          // 处理不同类型的字段定义
          // 类型1: { type: 'field', field_code: 'xxx', label: 'xxx' }
          if (item.type === 'field' && item.field_code) {
            fields.push({
              code: item.field_code,
              name: item.label || item.field_code
            })
          }
          // 类型2: { controlType: 'xxx', props: { code: 'xxx', label: 'xxx' } }
          else if (item.props && item.props.code) {
            fields.push({
              code: item.props.code,
              name: item.props.label || item.props.name || item.props.code
            })
          }
          
          // 递归处理子元素
          if (item.children && Array.isArray(item.children)) {
            fields.push(...extractFields(item.children))
          }
        }
        return fields
      }
      
      modelFields.value = extractFields(configArray)
    }
  } catch (error) {
    console.error('获取模型字段失败:', error)
  }
}

const addCondition = () => {
  if (!nodeConfig.filter_config.conditions) {
    nodeConfig.filter_config.conditions = []
  }
  nodeConfig.filter_config.conditions.push({
    field: '',
    operator: 'eq',
    value: ''
  })
}

const removeCondition = (index: number) => {
  nodeConfig.filter_config.conditions.splice(index, 1)
}

const handleSaveNodeConfig = async () => {
  try {
    await updateNode(selectedNode.value.id, {
      name: nodeConfig.name,
      sort_order: nodeConfig.sort_order,
      is_active: nodeConfig.is_active,
      filter_config: selectedNode.value.is_root ? null : nodeConfig.filter_config
    })
    message.success('保存成功')
    await fetchTreeData()
    if (selectedNode.value) {
      onSelect([selectedNode.value.id])
    }
  } catch (error: any) {
    message.error(error.response?.data?.message || '保存失败')
  }
}

const showGrantPermissionModal = () => {
  permissionForm.role_id = null
  permissionModalVisible.value = true
}

const handleGrantPermission = async () => {
  if (!permissionForm.role_id) {
    message.warning('请选择角色')
    return
  }
  try {
    await grantNodePermission(selectedNode.value.id, {
      role_id: permissionForm.role_id
    })
    message.success('授权成功')
    permissionModalVisible.value = false
    await fetchNodePermissions(selectedNode.value.id)
  } catch (error: any) {
    message.error(error.response?.data?.message || '授权失败')
  }
}

const handleRevokePermission = async (roleId: number) => {
  try {
    await revokeNodePermission(selectedNode.value.id, roleId)
    message.success('撤销成功')
    await fetchNodePermissions(selectedNode.value.id)
  } catch (error: any) {
    message.error(error.response?.data?.message || '撤销失败')
  }
}

const handleSave = () => {
  message.success('保存成功')
}

const goBack = () => {
  router.push('/system/custom-view')
}
</script>

<style scoped>
.view-designer-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.designer-header {
  margin-bottom: 0;
}

.designer-layout {
  height: calc(100vh - 180px);
}

.tree-sider {
  background: #fff;
  border-right: 1px solid #f0f0f0;
  overflow: auto;
}

.tree-header {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.tree-content {
  padding: 12px;
  overflow: auto;
  height: calc(100% - 50px);
}

.tree-node-title {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.tree-node-title:hover .node-actions {
  display: inline-flex;
}

.node-actions {
  display: none;
}

.config-content {
  padding: 0;
  overflow: auto;
  background: #fff;
}

.node-config {
  padding: 0;
}

.tip-box {
  padding: 16px;
}

.condition-item {
  margin-bottom: 8px;
}

.permission-config {
  padding: 16px;
}
</style>
