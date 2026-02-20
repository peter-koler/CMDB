<template>
  <div class="role-page">
    <a-card :bordered="false">
      <div class="search-bar">
        <a-space>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索角色名称或编码"
            style="width: 300px"
            @search="handleSearch"
          />
          <a-button type="primary" @click="showRoleModal()">
            <PlusOutlined />
            新增角色
          </a-button>
        </a-space>
      </div>

      <a-table
        :columns="columns"
        :data-source="roles"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'green' : 'red'">
              {{ record.status === 'active' ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'user_count'">
            <a-badge :count="record.user_count" show-zero />
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="showRoleModal(record)">
                编辑
              </a-button>
              <a-button type="link" size="small" @click="showPermissionModal(record)">
                配置权限
              </a-button>
              <a-button type="link" size="small" @click="showUserModal(record)">
                分配用户
              </a-button>
              <a-popconfirm title="确定删除该角色吗？" @confirm="handleDelete(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 角色编辑弹窗 -->
    <a-modal
      v-model:open="roleModalVisible"
      :title="isEdit ? '编辑角色' : '新增角色'"
      @ok="handleRoleSubmit"
    >
      <a-form :model="roleForm" :rules="roleRules" ref="roleFormRef">
        <a-form-item label="角色名称" name="name">
          <a-input v-model:value="roleForm.name" placeholder="请输入角色名称" />
        </a-form-item>
        <a-form-item label="角色编码" name="code">
          <a-input v-model:value="roleForm.code" placeholder="请输入角色编码" :disabled="isEdit" />
        </a-form-item>
        <a-form-item label="角色描述" name="description">
          <a-textarea v-model:value="roleForm.description" :rows="3" placeholder="请输入角色描述" />
        </a-form-item>
        <a-form-item label="状态" name="status">
          <a-radio-group v-model:value="roleForm.status">
            <a-radio value="active">启用</a-radio>
            <a-radio value="disabled">禁用</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 权限配置弹窗 -->
    <a-modal
      v-model:open="permissionModalVisible"
      title="配置权限"
      @ok="handlePermissionSubmit"
      width="700px"
    >
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="menu" tab="菜单权限">
          <a-tree
            v-model:checked-keys="checkedPermissions"
            :tree-data="menuTree"
            checkable
            :check-strictly="false"
            :field-names="{ title: 'title', key: 'key', children: 'children' }"
          />
        </a-tab-pane>
        <a-tab-pane key="data" tab="数据权限">
          <a-radio-group v-model:value="dataPermission.scope" style="width: 100%">
            <a-space direction="vertical">
              <a-radio value="all">全部数据</a-radio>
              <a-radio value="department_with_children">本部门及子部门</a-radio>
              <a-radio value="department_only">仅本部门</a-radio>
              <a-radio value="self">仅自己创建的数据</a-radio>
            </a-space>
          </a-radio-group>
          <div style="margin-top: 16px">
            <a-checkbox v-model:checked="dataPermission.inherit">
              继承上级部门数据权限
            </a-checkbox>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-modal>

    <!-- 分配用户弹窗 -->
    <a-modal
      v-model:open="userModalVisible"
      title="分配用户"
      @ok="handleAssignUsers"
      width="700px"
    >
      <a-transfer
        v-model:target-keys="targetUserKeys"
        :data-source="allUsers"
        :titles="['未分配用户', '已选用户']"
        :render="item => item.title"
        :list-style="{ width: '300px', height: '400px' }"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import {
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  getRoleUsers,
  addRoleUsers,
  removeRoleUser,
  getMenuTree
} from '@/api/role'
import { getUsers } from '@/api/user'

const loading = ref(false)
const roles = ref<any[]>([])
const searchKeyword = ref('')

const columns = [
  { title: '角色名称', dataIndex: 'name', key: 'name' },
  { title: '角色编码', dataIndex: 'code', key: 'code' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '用户数量', key: 'user_count', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '操作', key: 'action', width: 350 }
]

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 角色编辑
const roleModalVisible = ref(false)
const isEdit = ref(false)
const roleFormRef = ref()
const roleForm = reactive({
  id: null as number | null,
  name: '',
  code: '',
  description: '',
  status: 'active'
})

const roleRules = {
  name: [{ required: true, message: '请输入角色名称' }],
  code: [{ required: true, message: '请输入角色编码' }]
}

// 权限配置
const permissionModalVisible = ref(false)
const activeTab = ref('menu')
const currentRole = ref<any>(null)
const menuTree = ref<any[]>([])
const checkedPermissions = ref<string[]>([])
const dataPermission = reactive({
  scope: 'self',
  inherit: false
})

// 用户分配
const userModalVisible = ref(false)
const allUsers = ref<any[]>([])
const targetUserKeys = ref<string[]>([])

onMounted(() => {
  fetchRoles()
  fetchMenuTree()
  fetchAllUsers()
})

const fetchRoles = async () => {
  loading.value = true
  try {
    const res = await getRoles({
      page: pagination.current,
      per_page: pagination.pageSize,
      keyword: searchKeyword.value
    })
    if (res.code === 200) {
      roles.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchMenuTree = async () => {
  try {
    const res = await getMenuTree()
    if (res.code === 200) {
      menuTree.value = res.data
    }
  } catch (error) {
    console.error(error)
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

const handleSearch = () => {
  pagination.current = 1
  fetchRoles()
}

const showRoleModal = (role?: any) => {
  isEdit.value = !!role
  if (role) {
    Object.assign(roleForm, role)
  } else {
    Object.assign(roleForm, {
      id: null,
      name: '',
      code: '',
      description: '',
      status: 'active'
    })
  }
  roleModalVisible.value = true
}

const handleRoleSubmit = async () => {
  try {
    await roleFormRef.value.validate()
    
    if (isEdit.value) {
      await updateRole(roleForm.id!, roleForm)
      message.success('更新成功')
    } else {
      await createRole(roleForm)
      message.success('创建成功')
    }
    
    roleModalVisible.value = false
    fetchRoles()
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const showPermissionModal = (role: any) => {
  currentRole.value = role
  checkedPermissions.value = role.menu_permissions || []
  if (role.data_permissions) {
    dataPermission.scope = role.data_permissions.scope || 'self'
    dataPermission.inherit = role.data_permissions.inherit || false
  }
  permissionModalVisible.value = true
}

const handlePermissionSubmit = async () => {
  if (!currentRole.value) return
  
  try {
    await updateRole(currentRole.value.id, {
      menu_permissions: checkedPermissions.value,
      data_permissions: {
        scope: dataPermission.scope,
        inherit: dataPermission.inherit
      }
    })
    message.success('权限配置成功')
    permissionModalVisible.value = false
    fetchRoles()
  } catch (error: any) {
    message.error(error.response?.data?.message || '配置失败')
  }
}

const showUserModal = async (role: any) => {
  currentRole.value = role
  try {
    const res = await getRoleUsers(role.id)
    if (res.code === 200) {
      targetUserKeys.value = res.data.items.map((item: any) => String(item.user_id))
    }
    userModalVisible.value = true
  } catch (error) {
    console.error(error)
  }
}

const handleAssignUsers = async () => {
  if (!currentRole.value) return
  
  try {
    const currentIds = targetUserKeys.value.map(Number)
    await addRoleUsers(currentRole.value.id, { user_ids: currentIds, replace: true })
    message.success('分配成功')
    userModalVisible.value = false
    fetchRoles()
  } catch (error: any) {
    message.error(error.response?.data?.message || '分配失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await deleteRole(id)
    message.success('删除成功')
    fetchRoles()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}
</script>

<style scoped>
.role-page {
  height: 100%;
}

.search-bar {
  margin-bottom: 16px;
}
</style>
