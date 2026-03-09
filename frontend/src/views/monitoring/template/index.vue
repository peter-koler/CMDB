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
                <a-menu-item @click="showAddSubCategoryModal()" :disabled="!selectedCategoryForActions">
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
            <template #title="{ name, key, nodeType, count }">
              <div class="tree-node" @contextmenu.prevent="showContextMenu($event, key, nodeType)">
                <span class="node-name">{{ name }}</span>
                <span class="node-count" v-if="nodeType === 'category' && count > 0">
                  ({{ count }})
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
              <span class="template-name">{{ isNewTemplate ? t('template.addNewType') : getTemplateDisplayName(selectedTemplate) }}</span>
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
import * as yaml from 'js-yaml'
import {
  EyeOutlined,
  SaveOutlined,
  PlusOutlined,
  FolderOutlined,
  FolderAddOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'
import TemplatePreview from './components/TemplatePreview.vue'
import {
  getTemplates,
  getCategories,
  createTemplate as createTemplateApi,
  updateTemplate as updateTemplateApi,
  createCategory as createCategoryApi,
  updateCategory as updateCategoryApi,
  deleteCategory as deleteCategoryApi
} from '@/api/monitoring'

const { t, locale } = useI18n()

interface CategoryNode {
  id?: number
  key: string
  name: string
  icon?: string
  parent_id?: number
  children?: CategoryNode[]
}

interface TemplateItem {
  app: string
  category: string
  name: string | Record<string, string>
  content: string
  version?: number
  is_hidden?: boolean
}

interface TreeNode {
  key: string
  name: string
  nodeType: 'category' | 'template'
  children?: TreeNode[]
  count?: number
}

const categories = ref<CategoryNode[]>([])
const templates = ref<TemplateItem[]>([])
const selectedCategoryKeys = ref<string[]>([])
const selectedTemplate = ref<TemplateItem | null>(null)
const templateYaml = ref('')
const saving = ref(false)
const previewModalVisible = ref(false)
const currentCategoryKey = ref('')

const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuKey = ref('')

const categoryModalVisible = ref(false)
const categoryModalTitle = ref('')
const categoryForm = ref({ name: '', key: '', parentKey: '' })
const isEditMode = ref(false)
const isSubCategory = ref(false)

const isNewTemplate = computed(() => Boolean(!selectedTemplate.value && currentCategoryKey.value))
const categoryTreeData = computed<TreeNode[]>(() => buildDisplayTree(categories.value))

const currentCategory = computed(() => {
  const key = selectedCategoryKeys.value[0]
  if (!key) return null
  if (String(key).startsWith('tpl:')) {
    return selectedTemplate.value ? findCategoryByKey(selectedTemplate.value.category, categories.value) : null
  }
  return findCategoryByKey(key, categories.value)
})

const selectedCategoryForActions = computed(() => {
  const key = selectedCategoryKeys.value[0]
  if (!key) return null
  if (String(key).startsWith('tpl:')) {
    return selectedTemplate.value ? findCategoryByKey(selectedTemplate.value.category, categories.value) : null
  }
  return findCategoryByKey(key, categories.value)
})

const normalizeCode = (name: string) => {
  const normalized = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
  return normalized || `cat_${Date.now()}`
}

const findCategoryByKey = (key: string, list: CategoryNode[]): CategoryNode | null => {
  for (const item of list) {
    if (item.key === key) return item
    if (item.children?.length) {
      const found = findCategoryByKey(key, item.children)
      if (found) return found
    }
  }
  return null
}

const getTemplateByTreeKey = (key: string) => {
  if (!key.startsWith('tpl:')) return null
  const app = key.slice(4)
  return templates.value.find((item) => item.app === app) || null
}

const buildDisplayTree = (categoryNodes: CategoryNode[]): TreeNode[] => {
  return categoryNodes.map((cat) => {
    const categoryChildren = buildDisplayTree(cat.children || [])
    const templateChildren = templates.value
      .filter((t) => t.category === cat.key)
      .sort((a, b) => getTemplateDisplayName(a).localeCompare(getTemplateDisplayName(b)))
      .map<TreeNode>((tpl) => ({
        key: `tpl:${tpl.app}`,
        name: getTemplateDisplayName(tpl),
        nodeType: 'template'
      }))

    const subtreeCount = categoryChildren.reduce((sum, node) => sum + (node.count || 0), 0)
    const count = templateChildren.length + subtreeCount

    return {
      key: cat.key,
      name: cat.name,
      nodeType: 'category',
      count,
      children: [...categoryChildren, ...templateChildren]
    }
  })
}

const findFirstTemplateKey = (nodes: TreeNode[]): string | null => {
  for (const node of nodes) {
    if (node.nodeType === 'template') return node.key
    if (node.children?.length) {
      const nested = findFirstTemplateKey(node.children)
      if (nested) return nested
    }
  }
  return null
}

const getTemplateDisplayName = (tpl: TemplateItem | null) => {
  if (!tpl) return ''
  if (typeof tpl.name === 'string') return tpl.name || tpl.app
  return tpl.name?.[String(locale.value)] || tpl.name?.['zh-CN'] || tpl.name?.['en-US'] || tpl.app
}

const parseYamlObject = (content: string): any => {
  const doc = yaml.load(content || '')
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
    throw new Error('YAML 顶层必须是对象')
  }
  return doc
}

const normalizeTemplateYaml = (content: string, fallbackCategory = '') => {
  const doc = parseYamlObject(content)
  const app = String(doc.app || '').trim()
  const category = String(doc.category || fallbackCategory || '').trim()
  const nameNode = doc.name
  const name = typeof nameNode === 'string'
    ? nameNode.trim()
    : String(nameNode?.['zh-CN'] || nameNode?.['en-US'] || app).trim()

  if (!app) {
    throw new Error('模板缺少 app 字段')
  }
  if (!category) {
    throw new Error('模板缺少 category 字段')
  }

  const params = Array.isArray(doc.params) ? doc.params : []
  const seen = new Set<string>()
  const duplicates: string[] = []
  const deduped: any[] = []
  for (const item of params) {
    if (!item || typeof item !== 'object') continue
    const field = String((item as any).field || '').trim()
    if (!field) continue
    if (seen.has(field)) {
      duplicates.push(field)
      continue
    }
    seen.add(field)
    deduped.push(item)
  }
  doc.params = deduped

  return {
    app,
    category,
    name: name || app,
    content: yaml.dump(doc, { noRefs: true, sortKeys: false, lineWidth: -1 }),
    duplicates
  }
}

const buildCategoryTree = (rows: any[]): CategoryNode[] => {
  const byId = new Map<number, CategoryNode>()
  const roots: CategoryNode[] = []

  rows.forEach((row) => {
    const node: CategoryNode = {
      id: Number(row.id),
      key: String(row.code),
      name: String(row.name || row.code),
      icon: row.icon,
      parent_id: row.parent_id ? Number(row.parent_id) : undefined,
      children: []
    }
    byId.set(node.id as number, node)
  })

  rows.forEach((row) => {
    const node = byId.get(Number(row.id))
    if (!node) return
    const parentId = row.parent_id ? Number(row.parent_id) : undefined
    if (parentId && byId.has(parentId)) {
      byId.get(parentId)?.children?.push(node)
    } else {
      roots.push(node)
    }
  })

  return roots
}

const dedupeTemplatesByApp = (rows: any[]): TemplateItem[] => {
  const byApp = new Map<string, TemplateItem>()
  for (const row of rows || []) {
    const app = String(row?.app || '').trim()
    if (!app) continue
    byApp.set(app, {
      app,
      category: String(row?.category || '').trim(),
      name: row?.name || app,
      content: String(row?.content || ''),
      version: Number(row?.version || 0),
      is_hidden: Boolean(row?.is_hidden)
    })
  }
  return Array.from(byApp.values()).sort((a, b) => a.app.localeCompare(b.app))
}

const loadTemplates = async () => {
  try {
    const [tplResp, catResp] = await Promise.all([getTemplates(), getCategories()])

    templates.value = dedupeTemplatesByApp(tplResp?.data || [])
    categories.value = buildCategoryTree(catResp?.data || [])
    const selectedKey = selectedCategoryKeys.value[0]
    if (selectedKey?.startsWith('tpl:')) {
      const selectedTpl = getTemplateByTreeKey(selectedKey)
      if (selectedTpl) {
        selectTemplate(selectedTpl)
      } else {
        selectedCategoryKeys.value = []
        selectedTemplate.value = null
        templateYaml.value = ''
      }
      return
    }

    if (selectedKey && findCategoryByKey(selectedKey, categories.value)) {
      currentCategoryKey.value = selectedKey
      selectedTemplate.value = null
      templateYaml.value = ''
      return
    }

    const firstTplKey = findFirstTemplateKey(categoryTreeData.value)
    if (firstTplKey) {
      selectedCategoryKeys.value = [firstTplKey]
      const firstTpl = getTemplateByTreeKey(firstTplKey)
      if (firstTpl) {
        selectTemplate(firstTpl)
      }
      return
    }

    if (categories.value.length) {
      selectedCategoryKeys.value = [categories.value[0].key]
      currentCategoryKey.value = categories.value[0].key
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
    message.error(t('template.loadFailed'))
  }
}

const showContextMenu = (e: MouseEvent, key: string, nodeType: 'category' | 'template') => {
  if (nodeType !== 'category') return
  e.preventDefault()
  contextMenuKey.value = key
  contextMenuPosition.value = { x: e.clientX, y: e.clientY }
  contextMenuVisible.value = true
}

const hideContextMenu = () => {
  contextMenuVisible.value = false
}

const handleTreeRightClick = ({ event, node }: any) => {
  if (node?.nodeType !== 'category') return
  showContextMenu(event, String(node.key), 'category')
}

const showAddCategoryModal = () => {
  isEditMode.value = false
  isSubCategory.value = false
  categoryModalTitle.value = t('template.addCategory')
  categoryForm.value = { name: '', key: '', parentKey: '' }
  categoryModalVisible.value = true
}

const showAddSubCategoryModal = () => {
  const parentKey = selectedCategoryForActions.value?.key
  if (!parentKey) return
  isEditMode.value = false
  isSubCategory.value = true
  categoryModalTitle.value = t('template.addSubCategory')
  categoryForm.value = { name: '', key: '', parentKey }
  categoryModalVisible.value = true
}

const handleRenameCategory = () => {
  hideContextMenu()
  const category = findCategoryByKey(contextMenuKey.value, categories.value)
  if (!category) return
  isEditMode.value = true
  isSubCategory.value = Boolean(category.parent_id)
  categoryModalTitle.value = t('template.renameCategory')
  categoryForm.value = { name: category.name, key: category.key, parentKey: '' }
  categoryModalVisible.value = true
}

const handleAddSubCategory = () => {
  hideContextMenu()
  if (!contextMenuKey.value) return
  isEditMode.value = false
  isSubCategory.value = true
  categoryModalTitle.value = t('template.addSubCategory')
  categoryForm.value = { name: '', key: '', parentKey: contextMenuKey.value }
  categoryModalVisible.value = true
}

const handleDeleteCategory = () => {
  hideContextMenu()
  const key = contextMenuKey.value
  if (!key) return
  Modal.confirm({
    title: t('template.confirmDeleteCategory'),
    content: t('template.confirmDeleteCategoryContent'),
    okText: t('common.confirm'),
    cancelText: t('common.cancel'),
    onOk: async () => {
      try {
        await deleteCategoryApi(key)
        if (selectedCategoryKeys.value[0] === key) {
          selectedCategoryKeys.value = []
          selectedTemplate.value = null
          templateYaml.value = ''
        }
        await loadTemplates()
        message.success(t('template.deleteSuccess'))
      } catch (error: any) {
        message.error(error?.response?.data?.message || t('template.saveFailed'))
      }
    }
  })
}

const handleSaveCategory = async () => {
  const name = categoryForm.value.name.trim()
  if (!name) {
    message.error(t('template.categoryNameRequired'))
    return
  }

  try {
    if (isEditMode.value) {
      await updateCategoryApi(categoryForm.value.key, { name })
      message.success(t('template.saveSuccess'))
    } else {
      const parent = isSubCategory.value
        ? findCategoryByKey(categoryForm.value.parentKey, categories.value)
        : null
      const code = normalizeCode(name)
      await createCategoryApi({
        name,
        code,
        parent_id: parent?.id
      })
      message.success(t('template.addSuccess'))
    }
    categoryModalVisible.value = false
    await loadTemplates()
  } catch (error: any) {
    message.error(error?.response?.data?.message || t('template.saveFailed'))
  }
}

const handleCategorySelect = (keys: string[]) => {
  selectedCategoryKeys.value = keys
  hideContextMenu()

  const key = keys[0]
  if (!key) {
    selectedTemplate.value = null
    templateYaml.value = ''
    currentCategoryKey.value = ''
    return
  }

  if (key.startsWith('tpl:')) {
    const template = getTemplateByTreeKey(key)
    if (template) {
      selectTemplate(template)
      return
    }
    selectedTemplate.value = null
    templateYaml.value = ''
    return
  }

  currentCategoryKey.value = key
  selectedTemplate.value = null
  templateYaml.value = ''
}

const selectTemplate = (template: TemplateItem) => {
  selectedTemplate.value = template
  currentCategoryKey.value = template.category
  templateYaml.value = template.content || ''
}

const handleSave = async () => {
  const raw = templateYaml.value.trim()
  if (!raw) {
    message.warning('请输入模板内容')
    return
  }

  saving.value = true
  try {
    const normalized = normalizeTemplateYaml(raw, selectedTemplate.value?.category || currentCategoryKey.value)
    if (normalized.duplicates.length) {
      message.warning(`检测到重复 params 字段并自动去重: ${Array.from(new Set(normalized.duplicates)).join(', ')}`)
    }
    templateYaml.value = normalized.content

    if (isNewTemplate.value) {
      const resp = await createTemplateApi({
        app: normalized.app,
        name: normalized.name,
        category: normalized.category,
        content: normalized.content
      })
      if (resp.code != 200) {
        message.error(resp.message || t('template.saveFailed'))
        return
      }
      message.success(t('template.addSuccess') || '添加成功')
      await loadTemplates()
      selectedCategoryKeys.value = [`tpl:${normalized.app}`]
      const created = templates.value.find((t) => t.app === normalized.app)
      if (created) selectTemplate(created)
      return
    }

    if (!selectedTemplate.value) return
    const resp = await updateTemplateApi(selectedTemplate.value.app, {
      name: normalized.name,
      category: normalized.category,
      content: normalized.content
    })
    if (resp.code != 200) {
      message.error(resp.message || t('template.saveFailed'))
      return
    }
    message.success(t('template.saveSuccess'))
    await loadTemplates()
  } catch (error: any) {
    console.error('Save template error:', error)
    message.error(error?.message || t('template.saveFailed'))
  } finally {
    saving.value = false
  }
}

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
