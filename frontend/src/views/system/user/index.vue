<template>
  <div class="user-page">
    <div class="page-header">
      <h2>用户管理</h2>
    </div>
    
    <div class="search-bar">
      <a-space>
        <a-input-search
          v-model:value="searchKeyword"
          placeholder="搜索用户名/邮箱/手机号"
          style="width: 250px"
          @search="handleSearch"
        />
        <a-tree-select
          v-model:value="searchDept"
          :tree-data="departmentTree"
          :field-names="{ label: 'name', value: 'id', children: 'children' }"
          placeholder="选择部门"
          style="width: 180px"
          allowClear
          treeDefaultExpandAll
        />
        <a-select
          v-model:value="searchStatus"
          placeholder="状态"
          style="width: 120px"
          allowClear
        >
          <a-select-option value="active">正常</a-select-option>
          <a-select-option value="locked">锁定</a-select-option>
          <a-select-option value="disabled">禁用</a-select-option>
        </a-select>
        <a-button type="primary" @click="handleSearch">
          <SearchOutlined />
          搜索
        </a-button>
        <a-button @click="handleReset">重置</a-button>
      </a-space>
      <div class="header-actions">
        <a-button type="primary" @click="handleAdd">
          <PlusOutlined />
          新增用户
        </a-button>
      </div>
    </div>

    <a-table
      :columns="columns"
      :data-source="users"
      :loading="loading"
      :pagination="pagination"
      @change="handleTableChange"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'username'">
          <a-space>
            <a-avatar size="small" style="background-color: #1890ff">
              {{ record.username?.charAt(0)?.toUpperCase() }}
            </a-avatar>
            <span>{{ record.username }}</span>
          </a-space>
        </template>
        <template v-else-if="column.key === 'departments'">
          <a-space v-if="record.departments && record.departments.length > 0" wrap>
            <a-tag v-for="dept in record.departments.slice(0, 2)" :key="dept.id" size="small">
              {{ dept.name }}
            </a-tag>
            <a-tag v-if="record.departments.length > 2" size="small">+{{ record.departments.length - 2 }}</a-tag>
          </a-space>
          <span v-else>-</span>
        </template>
        <template v-else-if="column.key === 'roles'">
          <a-space v-if="record.roles && record.roles.length > 0" wrap>
            <a-tag v-for="role in record.roles.slice(0, 2)" :key="role.id" color="blue" size="small">
              {{ role.name }}
            </a-tag>
            <a-tag v-if="record.roles.length > 2" size="small">+{{ record.roles.length - 2 }}</a-tag>
          </a-space>
          <span v-else>-</span>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="getStatusColor(record.status)">
            {{ getStatusText(record.status) }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'created_at'">
          {{ formatDate(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space wrap>
            <a-button type="link" size="small" @click="handleEdit(record)">编辑</a-button>
            <a-button type="link" size="small" @click="handleResetPassword(record)">重置密码</a-button>
            <a-button type="link" size="small" @click="handleSetDept(record)">设置部门</a-button>
            <a-button type="link" size="small" @click="handleSetRole(record)">设置角色</a-button>
            <a-popconfirm
              v-if="record.username !== 'admin'"
              title="确定删除该用户吗？"
              @confirm="handleDelete(record)"
            >
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 用户编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      @ok="handleModalOk"
      :confirm-loading="modalLoading"
      width="600px"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        :label-col="{ span: 4 }"
        :wrapper-col="{ span: 20 }"
      >
        <a-form-item label="用户名" name="username" v-if="!isEdit">
          <a-input v-model:value="formState.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item label="密码" name="password" v-if="!isEdit">
          <a-input-password v-model:value="formState.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item label="邮箱" name="email">
          <a-input v-model:value="formState.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="手机号" name="phone">
          <a-input v-model:value="formState.phone" placeholder="请输入手机号" />
        </a-form-item>
        <a-form-item label="状态" name="status" v-if="isEdit">
          <a-select v-model:value="formState.status">
            <a-select-option value="active">正常</a-select-option>
            <a-select-option value="locked">锁定</a-select-option>
            <a-select-option value="disabled">禁用</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 设置部门弹窗 -->
    <a-modal
      v-model:open="deptModalVisible"
      title="设置部门"
      @ok="handleDeptOk"
      width="600px"
    >
      <a-transfer
        v-model:target-keys="selectedDeptKeys"
        :data-source="deptOptions"
        :titles="['未分配', '已分配']"
        :render="item => item.title"
        :list-style="{ width: '250px', height: '300px' }"
      />
    </a-modal>

    <!-- 设置角色弹窗 -->
    <a-modal
      v-model:open="roleModalVisible"
      title="设置角色"
      @ok="handleRoleOk"
      width="600px"
    >
      <a-transfer
        v-model:target-keys="selectedRoleKeys"
        :data-source="roleOptions"
        :titles="['未分配', '已分配']"
        :render="item => item.title"
        :list-style="{ width: '250px', height: '300px' }"
      />
    </a-modal>

    <!-- 重置密码弹窗 -->
    <a-modal
      v-model:open="resetPwdModalVisible"
      title="重置密码"
      @ok="handleResetPwdOk"
    >
      <a-form
        ref="resetPwdFormRef"
        :model="resetPwdForm"
        :rules="resetPwdRules"
      >
        <a-form-item label="新密码" name="new_password">
          <a-input-password v-model:value="resetPwdForm.new_password" placeholder="请输入新密码" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { getUsers, createUser, updateUser, deleteUser, resetPassword as resetUserPassword } from '@/api/user'
import { getDepartments } from '@/api/department'
import { getRoles } from '@/api/role'
import { addDepartmentUsers, removeDepartmentUser } from '@/api/department'
import { addRoleUsers, removeRoleUser } from '@/api/role'
import { getPasswordPolicy, validatePassword, getPasswordStrength } from '@/utils/password'

const columns = [
  { title: '用户名', key: 'username', width: 150 },
  { title: '邮箱', dataIndex: 'email', key: 'email', width: 180 },
  { title: '手机号', dataIndex: 'phone', key: 'phone', width: 120 },
  { title: '所属部门', key: 'departments', width: 180 },
  { title: '角色', key: 'roles', width: 150 },
  { title: '状态', key: 'status', width: 100 },
  { title: '创建时间', key: 'created_at', width: 170 },
  { title: '操作', key: 'action', width: 350 }
]

const loading = ref(false)
const users = ref<any[]>([])
const departmentTree = ref<any[]>([])
const searchKeyword = ref('')
const searchDept = ref<number | null>(null)
const searchStatus = ref('')

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

// 用户编辑
const modalVisible = ref(false)
const modalLoading = ref(false)
const isEdit = ref(false)
const currentUserId = ref<number | null>(null)
const formRef = ref()
const formState = reactive({
  username: '',
  password: '',
  email: '',
  phone: '',
  status: 'active'
})

const formRules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }],
  email: [{ type: 'email', message: '请输入有效的邮箱地址' }]
}

// 部门设置
const deptModalVisible = ref(false)
const deptOptions = ref<any[]>([])
const selectedDeptKeys = ref<string[]>([])

// 角色设置
const roleModalVisible = ref(false)
const roleOptions = ref<any[]>([])
const selectedRoleKeys = ref<string[]>([])

// 重置密码
const resetPwdModalVisible = ref(false)
const resetPwdFormRef = ref()
const resetPwdForm = reactive({
  new_password: ''
})

const resetPwdRules = {
  new_password: [{ required: true, message: '请输入新密码' }]
}

onMounted(() => {
  fetchUsers()
  fetchDepartments()
  fetchRoles()
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await getUsers({
      page: pagination.current,
      per_page: pagination.pageSize,
      keyword: searchKeyword.value,
      status: searchStatus.value
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

const fetchDepartments = async () => {
  try {
    const res = await getDepartments()
    if (res.code === 200) {
      departmentTree.value = res.data
      // 转换为一维列表用于穿梭框
      deptOptions.value = flattenDepartments(res.data)
    }
  } catch (error) {
    console.error(error)
  }
}

const flattenDepartments = (tree: any[], result: any[] = []) => {
  for (const item of tree) {
    result.push({ key: String(item.id), title: item.name })
    if (item.children && item.children.length > 0) {
      flattenDepartments(item.children, result)
    }
  }
  return result
}

const fetchRoles = async () => {
  try {
    const res = await getRoles({ per_page: 100 })
    if (res.code === 200) {
      roleOptions.value = res.data.items.map((role: any) => ({
        key: String(role.id),
        title: role.name
      }))
    }
  } catch (error) {
    console.error(error)
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchUsers()
}

const handleReset = () => {
  searchKeyword.value = ''
  searchDept.value = null
  searchStatus.value = ''
  handleSearch()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchUsers()
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(formState, {
    username: '',
    password: '',
    email: '',
    phone: '',
    status: 'active'
  })
  modalVisible.value = true
}

const handleEdit = (record: any) => {
  isEdit.value = true
  currentUserId.value = record.id
  Object.assign(formState, {
    username: record.username,
    email: record.email,
    phone: record.phone,
    status: record.status
  })
  modalVisible.value = true
}

const handleModalOk = async () => {
  try {
    await formRef.value.validate()
    modalLoading.value = true
    if (isEdit.value) {
      await updateUser(currentUserId.value!, {
        email: formState.email,
        phone: formState.phone,
        status: formState.status
      })
      message.success('更新成功')
    } else {
      if (formState.password) {
        const policy = await getPasswordPolicy()
        const validation = validatePassword(formState.password, policy)
        if (!validation.valid) {
          message.error(validation.message)
          modalLoading.value = false
          return
        }
      }
      await createUser(formState)
      message.success('创建成功')
    }
    modalVisible.value = false
    fetchUsers()
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

const handleSetDept = (record: any) => {
  currentUserId.value = record.id
  selectedDeptKeys.value = record.departments?.map((d: any) => String(d.id)) || []
  deptModalVisible.value = true
}

const handleDeptOk = async () => {
  if (!currentUserId.value) return
  
  try {
    // 获取当前用户的部门
    const user = users.value.find(u => u.id === currentUserId.value)
    const currentDepts = user?.departments?.map((d: any) => String(d.id)) || []
    
    // 找出新增的部门
    const newDepts = selectedDeptKeys.value.filter(id => !currentDepts.includes(id))
    for (const deptId of newDepts) {
      await addDepartmentUsers(Number(deptId), { user_ids: [currentUserId.value] })
    }
    
    // 找出移除的部门
    const removedDepts = currentDepts.filter((id: string) => !selectedDeptKeys.value.includes(id))
    for (const deptId of removedDepts) {
      await removeDepartmentUser(Number(deptId), currentUserId.value)
    }
    
    message.success('部门设置成功')
    deptModalVisible.value = false
    fetchUsers()
  } catch (error: any) {
    message.error(error.response?.data?.message || '设置失败')
  }
}

const handleSetRole = (record: any) => {
  currentUserId.value = record.id
  selectedRoleKeys.value = record.roles?.map((r: any) => String(r.id)) || []
  roleModalVisible.value = true
}

const handleRoleOk = async () => {
  if (!currentUserId.value) return
  
  try {
    const user = users.value.find(u => u.id === currentUserId.value)
    const currentRoles = user?.roles?.map((r: any) => String(r.id)) || []
    
    const newRoles = selectedRoleKeys.value.filter(id => !currentRoles.includes(id))
    for (const roleId of newRoles) {
      await addRoleUsers(Number(roleId), { user_ids: [currentUserId.value] })
    }
    
    const removedRoles = currentRoles.filter((id: string) => !selectedRoleKeys.value.includes(id))
    for (const roleId of removedRoles) {
      await removeRoleUser(Number(roleId), currentUserId.value)
    }
    
    message.success('角色设置成功')
    roleModalVisible.value = false
    fetchUsers()
  } catch (error: any) {
    message.error(error.response?.data?.message || '设置失败')
  }
}

const handleResetPassword = (record: any) => {
  currentUserId.value = record.id
  resetPwdForm.new_password = ''
  resetPwdModalVisible.value = true
}

const handleResetPwdOk = async () => {
  try {
    await resetPwdFormRef.value.validate()
    
    const policy = await getPasswordPolicy()
    const validation = validatePassword(resetPwdForm.new_password, policy)
    if (!validation.valid) {
      message.error(validation.message)
      return
    }
    
    await resetUserPassword(currentUserId.value!, resetPwdForm.new_password)
    message.success('密码重置成功')
    resetPwdModalVisible.value = false
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  }
}

const handleDelete = async (record: any) => {
  try {
    await deleteUser(record.id)
    message.success('删除成功')
    fetchUsers()
  } catch (error: any) {
    message.error(error.response?.data?.message || '删除失败')
  }
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'green',
    locked: 'red',
    disabled: 'default'
  }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    active: '正常',
    locked: '锁定',
    disabled: '禁用'
  }
  return texts[status] || status
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}
</script>

<style scoped>
.user-page {
  height: 100%;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}

.search-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
</style>
