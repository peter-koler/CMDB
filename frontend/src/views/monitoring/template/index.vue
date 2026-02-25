<template>
  <div class="monitoring-template-page">
    <div class="template-layout">
      <!-- 左侧分类树 -->
      <div class="category-sidebar">
        <div class="sidebar-header">
          <span class="title">{{ t('template.categories') }}</span>
          <a-dropdown>
            <a-button type="primary" size="small">
              <PlusOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="showAddCategoryModal()">
                  <FolderOutlined />
                  {{ t('template.addCategory') }}
                </a-menu-item>
                <a-menu-item @click="showAddSubCategoryModal()" :disabled="!selectedCategoryKeys[0]">
                  <FolderAddOutlined />
                  {{ t('template.addSubCategory') }}
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
        <div class="category-tree">
          <a-tree
            v-model:selectedKeys="selectedCategoryKeys"
            :tree-data="categoryTreeData"
            :field-names="{ title: 'name', key: 'key', children: 'children' }"
            @select="handleCategorySelect"
            @rightClick="handleTreeRightClick"
          >
            <template #title="{ name, key }">
              <div class="tree-node" @contextmenu.prevent="showContextMenu($event, key)">
                <span class="node-name">{{ name }}</span>
                <span class="node-count" v-if="getTemplateCount(key) > 0">
                  ({{ getTemplateCount(key) }})
                </span>
              </div>
            </template>
          </a-tree>
        </div>
      </div>

      <!-- 右键菜单 -->
      <div
        v-if="contextMenuVisible"
        class="context-menu"
        :style="{ left: contextMenuPosition.x + 'px', top: contextMenuPosition.y + 'px' }"
      >
        <a-menu>
          <a-menu-item @click="handleRenameCategory">
            <EditOutlined />
            {{ t('template.rename') }}
          </a-menu-item>
          <a-menu-item @click="handleAddSubCategory">
            <FolderAddOutlined />
            {{ t('template.addSubCategory') }}
          </a-menu-item>
          <a-menu-divider />
          <a-menu-item danger @click="handleDeleteCategory">
            <DeleteOutlined />
            {{ t('template.delete') }}
          </a-menu-item>
        </a-menu>
      </div>

      <!-- 右侧模板编辑器 -->
      <div class="template-editor">
        <div class="editor-header">
          <div class="header-left">
            <a-breadcrumb>
              <a-breadcrumb-item>{{ t('menu.monitoring') }}</a-breadcrumb-item>
              <a-breadcrumb-item>{{ t('menu.monitoringTemplate') }}</a-breadcrumb-item>
              <a-breadcrumb-item v-if="currentCategory">{{ currentCategory.name }}</a-breadcrumb-item>
            </a-breadcrumb>
            <div class="template-tabs" v-if="currentTemplates.length > 0">
              <div
                v-for="template in currentTemplates"
                :key="template.app"
                class="template-tab"
                :class="{ active: selectedTemplate?.app === template.app }"
                @click="selectTemplate(template)"
              >
                <FileTextOutlined />
                <span class="tab-name">{{ template.app }}.yml</span>
              </div>
            </div>
          </div>
          <div class="header-actions" v-if="selectedTemplate || isNewTemplate">
            <a-space>
              <a-button @click="handlePreview" v-if="selectedTemplate">
                <EyeOutlined />
                {{ t('template.preview') }}
              </a-button>
              <a-button type="primary" @click="handleSave" :loading="saving">
                <SaveOutlined />
                {{ t('template.saveAndApply') }}
              </a-button>
            </a-space>
          </div>
        </div>

        <div class="editor-content" v-if="selectedTemplate || isNewTemplate">
          <div class="editor-toolbar">
            <a-space>
              <a-tag color="blue">{{ isNewTemplate ? currentCategoryKey : selectedTemplate?.category }}</a-tag>
              <span class="template-name">{{ isNewTemplate ? t('template.addNewType') : (selectedTemplate?.name?.[locale] || selectedTemplate?.app) }}</span>
            </a-space>
          </div>
          <div class="code-editor-wrapper">
            <textarea
              v-model="templateYaml"
              class="code-textarea"
              :placeholder="isNewTemplate ? '# 请在此粘贴 YAML 模板内容...\n# 例如：\n# category: db\n# app: mysql\n# name:\n#   zh-CN: MySQL数据库\n#   en-US: MySQL Database\n# params:\n#   - name: host\n#     ...' : ''"
              spellcheck="false"
            />
          </div>
        </div>

        <div class="empty-state" v-else>
          <a-empty :description="t('template.selectTemplate')" />
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <a-modal
      v-model:open="previewModalVisible"
      :title="t('template.preview')"
      width="800px"
      :footer="null"
    >
      <template-preview :yaml-content="templateYaml" />
    </a-modal>

    <!-- 分类管理弹窗 -->
    <a-modal
      v-model:open="categoryModalVisible"
      :title="categoryModalTitle"
      @ok="handleSaveCategory"
      width="500px"
    >
      <a-form :model="categoryForm" layout="vertical">
        <a-form-item :label="t('template.categoryName')" required>
          <a-input
            v-model:value="categoryForm.name"
            :placeholder="t('template.categoryNamePlaceholder')"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { message, Modal } from 'ant-design-vue'
import {
  FileTextOutlined,
  EyeOutlined,
  SaveOutlined,
  PlusOutlined,
  FolderOutlined,
  FolderAddOutlined,
  EditOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  CloudOutlined,
  DesktopOutlined,
  GlobalOutlined,
  ClusterOutlined,
  CodeOutlined
} from '@ant-design/icons-vue'
import TemplatePreview from './components/TemplatePreview.vue'
import { getTemplates, getCategories, getTemplate } from '@/api/monitoring'

const { t, locale } = useI18n()

// 分类数据
const categories = ref([
  {
    key: 'db',
    name: t('template.categoryDb'),
    icon: DatabaseOutlined,
    children: [
      { key: 'db:mysql', name: 'MySQL', icon: DatabaseOutlined },
      { key: 'db:redis', name: 'Redis', icon: DatabaseOutlined },
      { key: 'db:postgresql', name: 'PostgreSQL', icon: DatabaseOutlined },
      { key: 'db:mongodb', name: 'MongoDB', icon: DatabaseOutlined }
    ]
  },
  {
    key: 'os',
    name: t('template.categoryOs'),
    icon: DesktopOutlined,
    children: [
      { key: 'os:linux', name: 'Linux', icon: DesktopOutlined },
      { key: 'os:windows', name: 'Windows', icon: DesktopOutlined }
    ]
  },
  {
    key: 'middleware',
    name: t('template.categoryMiddleware'),
    icon: ClusterOutlined,
    children: [
      { key: 'middleware:nginx', name: 'Nginx', icon: GlobalOutlined },
      { key: 'middleware:kafka', name: 'Kafka', icon: ClusterOutlined }
    ]
  },
  {
    key: 'custom',
    name: t('template.categoryCustom'),
    icon: CodeOutlined,
    children: []
  }
])

// 模板数据
const templates = ref<any[]>([])
const selectedCategoryKeys = ref<string[]>([])
const selectedTemplate = ref<any>(null)
const templateYaml = ref('')
const saving = ref(false)
const previewModalVisible = ref(false)
const currentCategoryKey = ref('')
const isNewTemplate = computed(() => !selectedTemplate.value && currentCategoryKey.value)

// 右键菜单
const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuKey = ref('')

// 分类管理弹窗
const categoryModalVisible = ref(false)
const categoryModalTitle = ref('')
const categoryForm = ref({ name: '', key: '', parentKey: '' })
const isEditMode = ref(false)
const isSubCategory = ref(false)

// 计算属性
const categoryTreeData = computed(() => categories.value)

const currentCategory = computed(() => {
  const key = selectedCategoryKeys.value[0]
  if (!key) return null
  for (const cat of categories.value) {
    if (cat.key === key) return cat
    if (cat.children) {
      const child = cat.children.find((c: any) => c.key === key)
      if (child) return child
    }
  }
  return null
})

const currentTemplates = computed(() => {
  const key = selectedCategoryKeys.value[0]
  if (!key) return []
  // 如果 key 包含 ":"，则是具体的模板；否则是分类
  if (key.includes(':')) {
    // 选择的是具体模板
    return templates.value.filter((t: any) => `${t.category}:${t.app}` === key)
  } else {
    // 选择的是分类
    return templates.value.filter((t: any) => t.category === key)
  }
})

// 获取模板数量
const getTemplateCount = (key: string) => {
  if (key.includes(':')) {
    return templates.value.filter((t: any) => `${t.category}:${t.app}` === key).length
  } else {
    return templates.value.filter((t: any) => t.category === key).length
  }
}

// 生成默认模板
const generateDefaultTemplate = (app: string, name: string) => {
  return `# 监控类型: ${name}
category: custom
app: ${app}
name:
  zh-CN: ${name}
  en-US: ${name}

params:
  - field: host
    name:
      zh-CN: 主机Host
      en-US: Host
    type: host
    required: true
  - field: port
    name:
      zh-CN: 端口
      en-US: Port
    type: number
    required: true

metrics:
  - name: basic
    priority: 0
    fields:
      - field: responseTime
        type: 0
        unit: ms
    protocol: http
    http:
      host: ^_^host^_^`
}

// 加载模板数据
const loadTemplates = async () => {
  try {
    // 从后端 API 获取模板列表
    const response = await getTemplates()
    console.log('Templates response:', response)
    if (response && response.code == 200 && response.data) {
      templates.value = response.data.map((item: any) => ({
        app: item.app,
        category: item.category,
        parentCategory: item.category.split(':')[0],
        name: item.name,
        content: item.content,
        version: item.version,
        is_hidden: item.is_hidden
      }))
      console.log('Parsed templates:', templates.value)
    }

    // 获取分类列表
    const catResponse = await getCategories()
    console.log('Categories response:', catResponse)
    if (catResponse && catResponse.code == 200 && catResponse.data) {
      // 构建分类树
      const categoryMap = new Map<string, any>()
      catResponse.data.forEach((cat: any) => {
        if (!cat.parent_id) {
          categoryMap.set(cat.code, {
            key: cat.code,
            name: cat.name,
            icon: getCategoryIcon(cat.icon),
            children: []
          })
        }
      })

      // 将模板添加到对应的分类下
      templates.value.forEach((tmpl: any) => {
        const parentKey = tmpl.parentCategory
        if (categoryMap.has(parentKey)) {
          categoryMap.get(parentKey).children.push({
            key: `${parentKey}:${tmpl.app}`,
            name: tmpl.name,
            app: tmpl.app
          })
        }
      })

      // 更新分类数据
      categories.value = Array.from(categoryMap.values())
      console.log('Final categories:', categories.value)
    }

    // 默认选中第一个模板
    console.log('After load - templates:', templates.value.length, 'categories:', categories.value.length)
    if (templates.value.length > 0 && !selectedTemplate.value) {
      // 选择第一个分类
      const firstCategory = categories.value[0]
      if (firstCategory && firstCategory.children && firstCategory.children.length > 0) {
        // 选择第一个子节点（具体模板）
        selectedCategoryKeys.value = [firstCategory.children[0].key]
        console.log('Auto selecting first template:', firstCategory.children[0])
        selectTemplate(templates.value.find((t: any) => `${t.category}:${t.app}` === firstCategory.children[0].key))
      } else if (firstCategory) {
        // 没有子节点，选择分类
        selectedCategoryKeys.value = [firstCategory.key]
      }
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
    message.error(t('template.loadFailed'))
  }
}

// 获取分类图标
const getCategoryIcon = (iconName?: string) => {
  const iconMap: Record<string, any> = {
    database: DatabaseOutlined,
    desktop: DesktopOutlined,
    cluster: ClusterOutlined,
    cloud: CloudOutlined,
    global: GlobalOutlined,
    code: CodeOutlined
  }
  return iconMap[iconName || 'code'] || CodeOutlined
}

// 显示右键菜单
const showContextMenu = (e: MouseEvent, key: string) => {
  e.preventDefault()
  contextMenuKey.value = key
  contextMenuPosition.value = { x: e.clientX, y: e.clientY }
  contextMenuVisible.value = true
}

// 隐藏右键菜单
const hideContextMenu = () => {
  contextMenuVisible.value = false
}

// 处理树节点右键点击
const handleTreeRightClick = ({ event, node }: any) => {
  showContextMenu(event, node.key)
}

// 显示新增分类弹窗
const showAddCategoryModal = () => {
  isEditMode.value = false
  isSubCategory.value = false
  categoryModalTitle.value = t('template.addCategory')
  categoryForm.value = { name: '', key: '', parentKey: '' }
  categoryModalVisible.value = true
}

// 显示新增子分类弹窗
const showAddSubCategoryModal = () => {
  const parentKey = selectedCategoryKeys.value[0]
  if (!parentKey) return
  isEditMode.value = false
  isSubCategory.value = true
  categoryModalTitle.value = t('template.addSubCategory')
  categoryForm.value = { name: '', key: '', parentKey }
  categoryModalVisible.value = true
}

// 处理重命名分类
const handleRenameCategory = () => {
  hideContextMenu()
  const key = contextMenuKey.value
  const category = findCategoryByKey(key)
  if (category) {
    isEditMode.value = true
    isSubCategory.value = key.includes(':')
    categoryModalTitle.value = t('template.renameCategory')
    categoryForm.value = { name: category.name, key, parentKey: '' }
    categoryModalVisible.value = true
  }
}

// 处理新增子分类（从右键菜单）
const handleAddSubCategory = () => {
  hideContextMenu()
  const parentKey = contextMenuKey.value
  isEditMode.value = false
  isSubCategory.value = true
  categoryModalTitle.value = t('template.addSubCategory')
  categoryForm.value = { name: '', key: '', parentKey }
  categoryModalVisible.value = true
}

// 处理删除分类
const handleDeleteCategory = () => {
  hideContextMenu()
  const key = contextMenuKey.value
  Modal.confirm({
    title: t('template.confirmDeleteCategory'),
    content: t('template.confirmDeleteCategoryContent'),
    okText: t('common.confirm'),
    cancelText: t('common.cancel'),
    onOk: () => {
      deleteCategory(key)
      message.success(t('template.deleteSuccess'))
    }
  })
}

// 查找分类
const findCategoryByKey = (key: string) => {
  for (const cat of categories.value) {
    if (cat.key === key) return cat
    if (cat.children) {
      const child = cat.children.find((c: any) => c.key === key)
      if (child) return child
    }
  }
  return null
}

// 删除分类
const deleteCategory = (key: string) => {
  // 删除主分类
  const mainIndex = categories.value.findIndex((c: any) => c.key === key)
  if (mainIndex > -1) {
    categories.value.splice(mainIndex, 1)
    if (selectedCategoryKeys.value[0] === key) {
      selectedCategoryKeys.value = []
      selectedTemplate.value = null
    }
    return
  }
  
  // 删除子分类
  for (const cat of categories.value) {
    if (cat.children) {
      const childIndex = cat.children.findIndex((c: any) => c.key === key)
      if (childIndex > -1) {
        cat.children.splice(childIndex, 1)
        if (selectedCategoryKeys.value[0] === key) {
          selectedCategoryKeys.value = [cat.key]
          if (currentTemplates.value.length > 0) {
            selectTemplate(currentTemplates.value[0])
          } else {
            selectedTemplate.value = null
            templateYaml.value = ''
          }
        }
        return
      }
    }
  }
}

// 保存分类
const handleSaveCategory = () => {
  if (!categoryForm.value.name) {
    message.error(t('template.categoryNameRequired'))
    return
  }
  
  if (isEditMode.value) {
    // 编辑模式
    const category = findCategoryByKey(categoryForm.value.key)
    if (category) {
      category.name = categoryForm.value.name
      message.success(t('template.saveSuccess'))
    }
  } else {
    // 新增模式
    const newKey = isSubCategory.value
      ? `${categoryForm.value.parentKey}:${categoryForm.value.name.toLowerCase().replace(/\s+/g, '_')}`
      : categoryForm.value.name.toLowerCase().replace(/\s+/g, '_')
    
    if (isSubCategory.value) {
      const newCategory = {
        key: newKey,
        name: categoryForm.value.name,
        icon: DatabaseOutlined
      }
      const parent = categories.value.find((c: any) => c.key === categoryForm.value.parentKey)
      if (parent) {
        if (!parent.children) parent.children = []
        parent.children.push(newCategory)
      }
    } else {
      const newCategory: any = {
        key: newKey,
        name: categoryForm.value.name,
        icon: ClusterOutlined,
        children: []
      }
      categories.value.push(newCategory)
    }
    message.success(t('template.addSuccess'))
  }
  
  categoryModalVisible.value = false
}

// 选择分类
const handleCategorySelect = (keys: string[]) => {
  console.log('Category selected:', keys, 'templates:', templates.value.length, 'categories:', categories.value.length)
  selectedCategoryKeys.value = keys
  hideContextMenu()
  console.log('currentTemplates:', currentTemplates.value.length, currentTemplates.value)
  
  const key = keys[0]
  if (!key) {
    selectedTemplate.value = null
    templateYaml.value = ''
    return
  }
  
  if (key.includes(':')) {
    // 选择的是具体模板
    if (currentTemplates.value.length > 0) {
      selectTemplate(currentTemplates.value[0])
    }
  } else {
    // 选择的是分类 - 显示空编辑器，允许新建模板
    selectedTemplate.value = null
    templateYaml.value = ''
    currentCategoryKey.value = key
  }
}

// 选择模板
const selectTemplate = (template: any) => {
  selectedTemplate.value = template
  templateYaml.value = template.content || ''
}

// 保存模板
const handleSave = async () => {
  if (!templateYaml.value.trim()) {
    message.warning('请输入模板内容')
    return
  }
  
  saving.value = true
  try {
    if (isNewTemplate.value) {
      // 新建模板 - 从 YAML 解析 app 和 name
      const yamlContent = templateYaml.value
      const appMatch = yamlContent.match(/^app:\s*(.+)$/m)
      const nameMatch = yamlContent.match(/name:\s*[\n\r]*\s*zh-CN:\s*(.+)$/m)
      
      if (!appMatch) {
        message.error('模板缺少 app 字段')
        saving.value = false
        return
      }
      
      const app = appMatch[1].trim()
      const name = nameMatch ? nameMatch[1].trim() : app
      
      // 调用后端 API 创建模板
      const { createTemplate: createTemplateApi } = await import('@/api/monitoring')
      const response = await createTemplateApi({
        app,
        name,
        category: currentCategoryKey.value,
        content: templateYaml.value
      })
      
      if (response.code == 200) {
        message.success(t('template.addSuccess') || '添加成功')
        // 刷新模板列表
        await loadTemplates()
        // 选中新创建的模板
        const newKey = `${currentCategoryKey.value}:${app}`
        selectedCategoryKeys.value = [newKey]
      } else {
        message.error(response.message || t('template.saveFailed'))
      }
    } else {
      // 更新现有模板
      const { updateTemplate: updateTemplateApi } = await import('@/api/monitoring')
      const response = await updateTemplateApi(selectedTemplate.value.app, {
        name: selectedTemplate.value.name,
        category: selectedTemplate.value.category,
        content: templateYaml.value
      })
      
      if (response.code == 200) {
        message.success(t('template.saveSuccess'))
        // 更新本地数据
        selectedTemplate.value.content = templateYaml.value
      } else {
        message.error(response.message || t('template.saveFailed'))
      }
    }
  } catch (error) {
    console.error('Save template error:', error)
    message.error(t('template.saveFailed'))
  } finally {
    saving.value = false
  }
}

// 预览
const handlePreview = () => {
  previewModalVisible.value = true
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped lang="scss">
.monitoring-template-page {
  height: 100%;
  padding: 16px;
  background: #f5f5f5;

  .template-layout {
    display: flex;
    height: calc(100vh - 120px);
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    overflow: hidden;

    .category-sidebar {
      width: 240px;
      border-right: 1px solid #f0f0f0;
      background: #fafafa;
      display: flex;
      flex-direction: column;

      .sidebar-header {
        padding: 16px;
        border-bottom: 1px solid #f0f0f0;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .title {
          font-weight: 600;
          font-size: 16px;
        }
      }

      .category-tree {
        flex: 1;
        overflow-y: auto;
        padding: 8px;

        .tree-node {
          display: flex;
          align-items: center;
          gap: 8px;

          .node-name {
            flex: 1;
          }

          .node-count {
            color: #999;
            font-size: 12px;
          }
        }
      }
    }

    .template-editor {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;

      .editor-header {
        padding: 16px;
        border-bottom: 1px solid #f0f0f0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #fff;

        .header-left {
          display: flex;
          flex-direction: column;
          gap: 12px;

          .template-tabs {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;

            .template-tab {
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 6px 12px;
              background: #f5f5f5;
              border-radius: 4px;
              cursor: pointer;
              transition: all 0.3s;

              &:hover {
                background: #e6f7ff;
              }

              &.active {
                background: #1890ff;
                color: #fff;
              }

              .tab-name {
                font-size: 13px;
              }
            }
          }
        }

        .header-actions {
          display: flex;
          gap: 8px;
        }
      }

      .editor-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 16px;
        overflow: hidden;

        .editor-toolbar {
          background: #fff;
          padding: 12px 16px;
          border-bottom: 1px solid #f0f0f0;
          border-radius: 4px 4px 0 0;

          .template-name {
            font-weight: 500;
            margin-left: 8px;
          }
        }

        .code-editor-wrapper {
          flex: 1;
          background: #1e1e1e;
          border-radius: 0 0 4px 4px;
          overflow: hidden;

          .code-textarea {
            width: 100%;
            height: 100%;
            padding: 16px;
            border: none;
            outline: none;
            background: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
            font-size: 14px;
            line-height: 1.6;
            resize: none;
            white-space: pre;
            overflow-wrap: normal;
            overflow: auto;
          }
        }
      }

      .empty-state {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
      }
    }
  }
}

// 右键菜单样式
.context-menu {
  position: fixed;
  z-index: 1000;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  min-width: 160px;

  :deep(.ant-menu) {
    border: none;
    border-radius: 4px;
  }
}
</style>
