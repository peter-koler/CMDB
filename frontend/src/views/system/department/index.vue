<template>
  <div class="department-page">
    <a-row :gutter="16" class="full-height">
      <!-- 左侧部门树 -->
      <a-col :xs="24" :sm="8" :md="6" :lg="5" class="tree-col">
        <a-card :bordered="false" class="tree-card" title="部门架构">
          <template #extra>
            <a-space>
              <a-button type="text" size="small" @click="showDeptModal()">
                <PlusOutlined />
              </a-button>
              <a-button type="text" size="small" @click="fetchDepartments">
                <ReloadOutlined />
              </a-button>
            </a-space>
          </template>
          <a-tree
            :tree-data="departmentTree"
            :selected-keys="selectedKeys"
            :expanded-keys="expandedKeys"
            :draggable="true"
            @select="onSelect"
            @expand="onExpand"
            @drop-info="onDrop"
            :field-names="{ title: 'name', key: 'id', children: 'children' }"
          >
            <template #title="{ name, id }">
              <a-dropdown :trigger="['contextmenu']">
                <span>{{ name }}</span>
                <template #overlay>
                  <a-menu @click="(e) => handleMenuClick(e, id)">
                    <a-menu-item key="add">添加子部门</a-menu-item>
                    <a-menu-item key="edit">编辑</a-menu-item>
                    <a-menu-item key="delete" danger>删除</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </template>
          </a-tree>
        </a-card>
      </a-col>

      <!-- 右侧用户列表 -->
      <a-col :xs="24" :sm="16" :md="18" :lg="19" class="content-col">
        <a-card :bordered="false" class="table-card">
          <template #title>
            {{ currentDept ? currentDept.name : '请选择部门' }} - 用户列表
          </template>
          <template #extra>
            <a-button type="primary" @click="showUserModal" :disabled="!currentDeptId">
              <PlusOutlined />
              添加用户
            </a-button>
          </template>
          
          <a-table
            :columns="columns"
            :data-source="users"
            :loading="loading"
            :pagination="pagination"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'roles'">
                <a-space v-if="record.user?.roles && record.user.roles.length > 0" wrap>
                  <a-tag v-for="role in record.user.roles.slice(0, 2)" :key="role.id" color="blue" size="small">
                    {{ role.name }}
                  </a-tag>
                  <a-tag v-if="record.user.roles.length > 2" size="small">+{{ record.user.roles.length - 2 }}</a-tag>
                </a-space>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'is_leader'">
                <a-tag v-if="record.is_leader" color="blue">负责人</a-tag>
                <span v-else>-</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="toggleLeader(record)">
                    {{ record.is_leader ? '取消负责人' : '设为负责人' }}
                  </a-button>
                  <a-popconfirm title="确定移除此用户？" @confirm="removeUser(record.user_id)">
                    <a-button type="link" size="small" danger>移除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- 部门编辑弹窗 -->
    <a-modal
      v-model:open="deptModalVisible"
      :title="isEditDept ? '编辑部门' : '新增部门'"
      @ok="handleDeptSubmit"
    >
      <a-form :model="deptForm" :rules="deptRules" ref="deptFormRef">
        <a-form-item label="部门名称" name="name">
          <a-input v-model:value="deptForm.name" placeholder="请输入部门名称" />
        </a-form-item>
        <a-form-item label="部门编码" name="code">
          <a-input v-model:value="deptForm.code" placeholder="请输入部门编码" :disabled="isEditDept" />
        </a-form-item>
        <a-form-item label="排序" name="sort_order">
          <a-input-number v-model:value="deptForm.sort_order" :min="0" style="width: 100%" />
        </a-form-item>
        <a-form-item label="部门角色" name="role_ids">
          <a-select
            v-model:value="deptForm.role_ids"
            mode="multiple"
            placeholder="请选择部门角色"
            :options="roleOptions"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item>
          <a-alert message="选择部门角色后，该部门的用户将自动获得这些角色" type="info" show-icon />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 添加用户弹窗 -->
    <a-modal
      v-model:open="userModalVisible"
      title="添加用户到部门"
      @ok="handleAddUsers"
      width="700px"
    >
      <a-transfer
        v-model:target-keys="targetKeys"
        :data-source="allUsers"
        :titles="['未分配用户', '已选用户']"
        :render="item => item.title"
        :list-style="{ width: '300px', height: '400px' }"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import {
  getDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  getDepartmentUsers,
  addDepartmentUsers,
  removeDepartmentUser,
  updateDepartmentUser,
  updateDepartmentSort
} from '@/api/department'
import { getUsers } from '@/api/user'
import { getRoles } from '@/api/role'

const departmentTree = ref<any[]>([])
const selectedKeys = ref<string[]>([])
const expandedKeys = ref<string[]>([])
const currentDeptId = ref<number | null>(null)
const currentDept = computed(() => findDept(departmentTree.value, currentDeptId.value))

const loading = ref(false)
const users = ref<any[]>([])
const allUsers = ref<any[]>([])
const targetKeys = ref<string[]>([])
const roleOptions = ref<any[]>([])

const columns = [
  { title: '用户名', dataIndex: ['user', 'username'], key: 'username' },
  { title: '邮箱', dataIndex: ['user', 'email'], key: 'email' },
  { title: '角色', key: 'roles', width: 200 },
  { title: '身份', key: 'is_leader', width: 100 },
  { title: '加入时间', dataIndex: 'joined_at', key: 'joined_at' },
  { title: '操作', key: 'action', width: 200 }
]

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

// 部门编辑
const deptModalVisible = ref(false)
const isEditDept = ref(false)
const deptFormRef = ref()
const deptForm = reactive({
  id: null as number | null,
  name: '',
  code: '',
  parent_id: null as number | null,
  sort_order: 0,
  role_ids: [] as number[]
})

const deptRules = {
  name: [{ required: true, message: '请输入部门名称' }],
  code: [{ required: true, message: '请输入部门编码' }]
}

const userModalVisible = ref(false)

onMounted(() => {
  fetchDepartments()
  fetchAllUsers()
  fetchRoles()
})

const fetchRoles = async () => {
  try {
    const res = await getRoles({ per_page: 100 })
    if (res.code === 200) {
      roleOptions.value = res.data.items.map((role: any) => ({
        value: role.id,
        label: role.name
      }))
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchDepartments = async () => {
  try {
    const res = await getDepartments()
    if (res.code === 200) {
      departmentTree.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchUsers = async () => {
  if (!currentDeptId.value) return
  
  loading.value = true
  try {
    const res = await getDepartmentUsers(currentDeptId.value, {
      page: pagination.current,
      per_page: pagination.pageSize
    })
    if (res.code === 200) {
      users.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchAllUsers = async () => {
  try {
    const res = await getUsers({ per_page: 1000 })
    if (res.code === 200) {
      allUsers.value = res.data.items.map((user: any) => ({
        key: String(user.id),
        title: user.username,
        description: user.email
      }))
    }
  } catch (error) {
    console.error(error)
  }
}

const onSelect = (keys: any) => {
  selectedKeys.value = keys
  currentDeptId.value = keys[0] || null
  if (currentDeptId.value) {
    fetchUsers()
  }
}

const onExpand = (keys: any) => {
  expandedKeys.value = keys
}

interface DropEvent {
  node: {
    key: string | number
    dragNode: {
      key: string | number
    }
    pos: string
  }
  dropPosition: number
}

const onDrop = async (info: DropEvent) => {
  const dropKey = Number(info.node.key)
  const dragKey = Number(info.node.dragNode.key)
  
  if (dropKey === dragKey) return
  
  const dropPos = info.node.pos.split('-')
  const dropPosition = info.node.pos.length - Number(dropPos[dropPos.length - 1])
  
  const loop = (data: any[], key: number, callback: (item: any, index: number, arr: any[]) => void) => {
    for (let i = 0; i < data.length; i++) {
      if (data[i].id === key) {
        callback(data[i], i, data)
        return
      }
      if (data[i].children) {
        loop(data[i].children, key, callback)
      }
    }
  }
  
  const dragObj = ref<any>({})
  
  loop(departmentTree.value, dragKey, (item) => {
    dragObj.value = item
  })
  
  const data = JSON.parse(JSON.stringify(departmentTree.value))
  
  let ar: any[] = []
  let i = 0
  loop(data, dragKey, (item, index, arr) => {
    ar = arr
    i = index
  })
  
  if (info.node.pos.includes('0-') || dropPosition === 0) {
    departmentTree.value = data
    const updateData = data.map((item: any, idx: number) => ({
      id: item.id,
      sort_order: idx
    }))
    try {
      await updateDepartmentSort(updateData)
      message.success('排序更新成功')
    } catch (error) {
      console.error(error)
      message.error('排序更新失败')
    }
  } else {
    let ar: any[] = []
    let i = 0
    let notch = 0
    loop(data, dropKey, (item, index, arr) => {
      ar = arr
      i = index
      notch = index
    })
    
    if (dropPosition === -1) {
      ar.splice(i - 1, 0, dragObj.value)
    } else {
      ar.splice(i + 1, 0, dragObj.value)
    }
    
    const updateData = ar.map((item: any, idx: number) => ({
      id: item.id,
      sort_order: idx
    }))
    
    try {
      await updateDepartmentSort(updateData)
      departmentTree.value = data
      message.success('排序更新成功')
    } catch (error) {
      console.error(error)
      message.error('排序更新失败')
    }
  }
}

const findDept = (tree: any[], id: number | null): any => {
  if (!id) return null
  for (const item of tree) {
    if (item.id === id) return item
    if (item.children) {
      const found = findDept(item.children, id)
      if (found) return found
    }
  }
  return null
}

const handleMenuClick = (e: any, id: number) => {
  if (e.key === 'add') {
    showDeptModal(null, id)
  } else if (e.key === 'edit') {
    const dept = findDept(departmentTree.value, id)
    if (dept) showDeptModal(dept)
  } else if (e.key === 'delete') {
    handleDeleteDept(id)
  }
}

const showDeptModal = (dept?: any, parentId?: number) => {
  isEditDept.value = !!dept
  if (dept) {
    Object.assign(deptForm, {
      id: dept.id,
      name: dept.name,
      code: dept.code,
      parent_id: dept.parent_id,
      sort_order: dept.sort_order,
      role_ids: dept.role_ids || []
    })
  } else {
    Object.assign(deptForm, {
      id: null,
      name: '',
      code: '',
      parent_id: parentId || null,
      sort_order: 0,
      role_ids: []
    })
  }
  deptModalVisible.value = true
}

const handleDeptSubmit = async () => {
  try {
    await deptFormRef.value.validate()
    
    if (isEditDept.value) {
      await updateDepartment(deptForm.id!, deptForm)
      message.success('更新成功')
    } else {
      await createDepartment(deptForm)
      message.success('创建成功')
    }
    
    deptModalVisible.value = false
    fetchDepartments()
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const handleDeleteDept = async (id: number) => {
  try {
    await deleteDepartment(id)
    message.success('删除成功')
    fetchDepartments()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const showUserModal = () => {
  targetKeys.value = users.value.map((u: any) => String(u.user_id))
  userModalVisible.value = true
}

const handleAddUsers = async () => {
  if (!currentDeptId.value) return
  
  try {
    // 找出新增的用户
    const currentUserIds = users.value.map((u: any) => String(u.user_id))
    const newUserIds = targetKeys.value.filter((id: string) => !currentUserIds.includes(id))
    
    if (newUserIds.length > 0) {
      await addDepartmentUsers(currentDeptId.value, {
        user_ids: newUserIds.map(Number)
      })
      message.success(`成功添加 ${newUserIds.length} 个用户`)
      fetchUsers()
    }
    
    userModalVisible.value = false
  } catch (error: any) {
    message.error(error.response?.data?.message || '添加失败')
  }
}

const removeUser = async (userId: number) => {
  if (!currentDeptId.value) return
  
  try {
    await removeDepartmentUser(currentDeptId.value, userId)
    message.success('移除成功')
    fetchUsers()
  } catch (error: any) {
    message.error(error.response?.data?.message || '移除失败')
  }
}

const toggleLeader = async (record: any) => {
  if (!currentDeptId.value) return
  
  try {
    await updateDepartmentUser(currentDeptId.value, record.user_id, {
      is_leader: !record.is_leader
    })
    message.success('设置成功')
    fetchUsers()
  } catch (error: any) {
    message.error(error.response?.data?.message || '设置失败')
  }
}
</script>

<style scoped>
.department-page {
  height: 100%;
}

.full-height {
  height: 100%;
}

.tree-col {
  height: 100%;
}

.content-col {
  height: 100%;
}

.tree-card {
  height: 100%;
}

.tree-card :deep(.ant-card-body) {
  height: calc(100% - 56px);
  overflow: auto;
}

.table-card {
  height: 100%;
}
</style>
