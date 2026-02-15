<template>
  <a-modal
    v-model:open="visible"
    :title="isEdit ? '编辑CI' : (isCopy ? '复制CI' : '新增CI')"
    @ok="handleOk"
    @cancel="handleCancel"
    :confirm-loading="loading"
    width="800px"
  >
    <a-form
      ref="formRef"
      :model="formState"
      :rules="formRules"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 18 }"
    >
      <a-form-item label="CI编码" name="code">
        <a-input v-model:value="formState.code" disabled />
      </a-form-item>
      <a-form-item label="所属部门" name="department_id">
        <a-tree-select
          v-model:value="formState.department_id"
          :tree-data="departmentTree"
          :field-names="{ label: 'name', value: 'id', children: 'children' }"
          placeholder="请选择部门"
          style="width: 100%"
          allowClear
        />
      </a-form-item>

      <!-- 动态字段 -->
      <div v-if="modelFields.length === 0" style="padding: 16px; color: #999;">
        暂无属性字段配置
      </div>
      <div v-else>
        <a-divider orientation="left">属性信息</a-divider>
        <div class="field-groups">
          <div
            v-for="section in groupedFieldSections"
            :key="section.key"
            class="field-group-card"
          >
            <div class="field-group-title">{{ section.label }}</div>
            <a-row :gutter="16">
              <a-col v-for="field in section.fields" :key="field.id" :span="field.span || 12">
                <a-form-item :label="field.name" :required="field.required">
              <!-- 文本输入 -->
              <a-input
                v-if="field.field_type === 'text'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请输入${field.name}`"
              />
              
              <!-- 数字输入 -->
              <a-input-number
                v-else-if="field.field_type === 'number'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请输入${field.name}`"
                style="width: 100%"
              />
              
              <!-- 布尔值 -->
              <a-switch
                v-else-if="field.field_type === 'boolean'"
                v-model:checked="formState.attribute_values[field.code]"
              />
              
              <!-- 密码 -->
              <a-input-password
                v-else-if="field.field_type === 'password'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请输入${field.name}`"
              />
              
              <!-- IP地址 -->
              <a-input
                v-else-if="field.field_type === 'ip'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请输入${field.name}，如：192.168.1.1`"
              />
              
              <!-- URL -->
              <a-input
                v-else-if="field.field_type === 'url'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请输入${field.name}，如：https://example.com`"
              />
              
              <!-- 下拉选择 -->
              <a-select
                v-else-if="field.field_type === 'select'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请选择${field.name}`"
                allowClear
              >
                <a-select-option v-for="opt in getFieldOptions(field)" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-select-option>
              </a-select>
              
              <!-- 多选 -->
              <a-select
                v-else-if="field.field_type === 'multiselect'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请选择${field.name}`"
                mode="multiple"
                allowClear
              >
                <a-select-option v-for="opt in getFieldOptions(field)" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-select-option>
              </a-select>

              <!-- 人员 -->
              <a-select
                v-else-if="field.field_type === 'user'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请选择${field.name}`"
                :mode="field.mode === 'multiple' ? 'multiple' : undefined"
                :options="getUserOptions(field)"
                allowClear
                show-search
                option-filter-prop="label"
              />
              
              <!-- 级联选择 -->
              <a-cascader
                v-else-if="field.field_type === 'cascade'"
                v-model:value="formState.attribute_values[field.code]"
                :options="getFieldOptions(field)"
                :placeholder="field.placeholder || `请选择${field.name}`"
                :load-data="(selectedOptions: any) => loadCascadeData(selectedOptions, field)"
              />
              
              <!-- 引用类型 -->
              <a-select
                v-else-if="field.field_type === 'reference'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="field.placeholder || `请选择${field.name}`"
                show-search
                :filter-option="false"
                @search="(val: string) => handleReferenceSearch(val, field)"
                allowClear
              >
                <a-select-option v-for="item in referenceOptions[field.id] || []" :key="item.id" :value="item.id">
                  {{ item.name }}
                </a-select-option>
              </a-select>
              
              <!-- 日期 -->
              <a-date-picker
                v-else-if="field.field_type === 'date'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="`请选择${field.name}`"
                style="width: 100%"
              />
              
              <!-- 日期时间 -->
              <a-date-picker
                v-else-if="field.field_type === 'datetime'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="`请选择${field.name}`"
                show-time
                style="width: 100%"
              />
              
              <!-- 富文本 -->
              <a-textarea
                v-else-if="field.field_type === 'richtext'"
                v-model:value="formState.attribute_values[field.code]"
                :placeholder="`请输入${field.name}`"
                :rows="4"
              />
              
              <!-- 文件上传 -->
              <a-upload
                v-else-if="field.field_type === 'file'"
                :file-list="getFileList(field.code)"
                :custom-request="(options: any) => handleUpload(options, field)"
                @remove="(file: any) => handleRemoveFile(file, field)"
              >
                <a-button>
                  <UploadOutlined />
                  上传文件
                </a-button>
              </a-upload>
              
              <!-- 图片上传 -->
              <a-upload
                v-else-if="field.field_type === 'image'"
                :file-list="getFileList(field.code)"
                :custom-request="(options: any) => handleUpload(options, field)"
                @remove="(file: any) => handleRemoveFile(file, field)"
                list-type="picture-card"
              >
                <div v-if="!getFileList(field.code)?.length">
                  <PlusOutlined />
                  <div style="margin-top: 8px">上传</div>
                </div>
              </a-upload>
                </a-form-item>
              </a-col>
            </a-row>
          </div>
        </div>
      </div>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { createInstance, updateInstance, generateCICode } from '@/api/ci'
import { getDictItemsByTypeCode, getModelDetail } from '@/api/cmdb'
import { getDepartments } from '@/api/department'
import { getInstances } from '@/api/ci'
import { uploadFile } from '@/api/ci'
import { getUsers } from '@/api/user'

interface Props {
  visible: boolean
  modelId: number | null
  instance: any | null
}

const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'success'])

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const loading = ref(false)
const isEdit = computed(() => !!props.instance && props.instance.id !== null && props.instance.id !== undefined)
const isCopy = computed(() => !!props.instance && (props.instance.id === null || props.instance.id === undefined))
const formRef = ref()
const formState = reactive({
  id: null as number | null,
  code: '',
  department_id: null as number | null,
  attribute_values: {} as Record<string, any>
})

const formRules = {
  code: [{ required: true, message: 'CI编码不能为空' }]
}

const modelFields = ref<any[]>([])
const departmentTree = ref<any[]>([])
const referenceOptions = ref<Record<number, any[]>>({})
const dictOptionsMap = ref<Record<string, { label: string; value: string }[]>>({})
const systemUserOptions = ref<{ label: string; value: number }[]>([])
const groupedFieldSections = computed(() => {
  const groups = new Map<string, { key: string; label: string; order: number; fields: any[] }>()
  groups.set('__base__', {
    key: '__base__',
    label: '基础属性',
    order: -1,
    fields: []
  })

  modelFields.value.forEach((field: any, index: number) => {
    const groupKey = field.group_id || '__base__'
    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        key: groupKey,
        label: field.group_label || '属性分组',
        order: field.group_order ?? index,
        fields: []
      })
    }
    groups.get(groupKey)!.fields.push(field)
  })

  return Array.from(groups.values())
    .filter((section) => section.fields.length > 0)
    .sort((a, b) => a.order - b.order)
})

watch(() => props.visible, (val) => {
  if (val) {
    initForm()
  }
})

watch(() => props.modelId, (val) => {
  if (val) {
    fetchModelDetail()
  }
})

watch(() => props.visible, (val) => {
  if (val) {
    initForm()
  }
})

onMounted(() => {
  fetchDepartments()
  loadSystemUsers()
})

const initForm = async () => {
  if (isEdit.value) {
    formState.id = props.instance.id
    formState.code = props.instance.code
    formState.department_id = props.instance.department_id
    formState.attribute_values = { ...props.instance.attributes, ...props.instance.attribute_values }
  } else if (isCopy.value) {
    formState.id = null
    formState.code = props.instance.code || ''
    formState.department_id = props.instance.department_id ?? null
    formState.attribute_values = { ...props.instance.attributes, ...props.instance.attribute_values }
    if (!formState.code) {
      try {
        const res = await generateCICode()
        if (res.code === 200) {
          formState.code = res.data.code
        }
      } catch (error) {
        console.error(error)
      }
    }
  } else {
    formState.id = null
    formState.department_id = null
    formState.attribute_values = {}
    
    try {
      const res = await generateCICode()
      if (res.code === 200) {
        formState.code = res.data.code
      }
    } catch (error) {
      console.error(error)
    }
  }
  
  if (props.modelId) {
    fetchModelDetail()
  }
}

const flattenDictTree = (nodes: any[]): { label: string; value: string }[] => {
  const result: { label: string; value: string }[] = []
  const walk = (items: any[], parentLabel = '') => {
    items.forEach((item) => {
      const currentLabel = parentLabel ? `${parentLabel} / ${item.label}` : item.label
      result.push({
        label: currentLabel,
        value: item.code
      })
      if (Array.isArray(item.children) && item.children.length > 0) {
        walk(item.children, currentLabel)
      }
    })
  }
  walk(nodes || [])
  return result
}

const ensureDictionaryOptionsLoaded = async (dictCode?: string) => {
  if (!dictCode || dictOptionsMap.value[dictCode]) return
  try {
    const res = await getDictItemsByTypeCode(dictCode, { enabled: true })
    if (res.code === 200) {
      dictOptionsMap.value[dictCode] = flattenDictTree(res.data?.items || [])
    }
  } catch (error) {
    console.error(error)
    dictOptionsMap.value[dictCode] = []
  }
}

const loadSystemUsers = async () => {
  try {
    const res = await getUsers({ page: 1, per_page: 1000 })
    if (res.code === 200) {
      const items = res.data?.items || []
      systemUserOptions.value = items.map((item: any) => ({
        label: item.username,
        value: item.id
      }))
    }
  } catch (error) {
    console.error(error)
  }
}

const normalizeOptions = (options: any): { label: string; value: any }[] => {
  if (!Array.isArray(options)) return []
  return options
    .map((item: any) => ({
      label: item?.label ?? item?.name ?? item?.value,
      value: item?.value ?? item?.code ?? item?.id
    }))
    .filter((item) => item.label !== undefined && item.value !== undefined)
}

const extractFieldsFromFormConfig = (formConfig: any[]): any[] => {
  const fields: any[] = []
  const walk = (items: any[], groupMeta?: { id: string; label: string; order: number }) => {
    items.forEach((item: any, index: number) => {
      if (item?.controlType === 'group' && Array.isArray(item.children)) {
        walk(item.children, {
          id: item.id || `group_${index}`,
          label: item.props?.label || '属性分组',
          order: index
        })
        return
      }
      if (!item?.props?.code) return
      fields.push({
        id: item.id || `field_${index}_${item.props.code}`,
        code: item.props.code,
        name: item.props.label || item.props.code,
        field_type: mapControlTypeToFieldType(item.controlType),
        control_type: item.controlType,
        required: item.props.required || false,
        default_value: item.props.defaultValue,
        placeholder: item.props.placeholder || '',
        span: item.props.span || 12,
        sort_order: index,
        mode: item.props.mode || 'multiple',
        option_type: item.props.optionType || 'custom',
        dictionary_code: item.props.dictionaryCode || '',
        options: normalizeOptions(item.props.options),
        user_ids: Array.isArray(item.props.userIds) ? item.props.userIds : [],
        group_id: groupMeta?.id || '__base__',
        group_label: groupMeta?.label || '基础属性',
        group_order: groupMeta?.order ?? -1
      })
    })
  }
  walk(formConfig || [])
  return fields
}

const fetchModelDetail = async () => {
  if (!props.modelId) return
  
  try {
    const res = await getModelDetail(props.modelId)
    if (res.code === 200) {
      // 优先使用 form_config（模型设计器配置）
      let formConfig = res.data.form_config
      if (formConfig) {
        // form_config 可能是双重编码的字符串
        if (typeof formConfig === 'string') {
          formConfig = JSON.parse(formConfig)
        }
        if (typeof formConfig === 'string') {
          formConfig = JSON.parse(formConfig)
        }
      } else {
        formConfig = []
      }
      
      if (formConfig.length > 0) {
        modelFields.value = extractFieldsFromFormConfig(formConfig)
        for (const field of modelFields.value) {
          if (field.option_type === 'dictionary' && field.dictionary_code) {
            await ensureDictionaryOptionsLoaded(field.dictionary_code)
            field.options = dictOptionsMap.value[field.dictionary_code] || []
          }
        }
      } else {
        // 使用传统的 regions/fields
        modelFields.value = res.data.fields || []
      }
      
      // 设置默认值
      modelFields.value.forEach(field => {
        if (field.default_value && !formState.attribute_values[field.code]) {
          formState.attribute_values[field.code] = field.default_value
        }
      })
    }
  } catch (error) {
    console.error(error)
  }
}

// 将控件类型映射为字段类型
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

const getFieldOptions = (field: any) => {
  if (Array.isArray(field.options)) {
    return field.options
  }
  try {
    return JSON.parse(field.options || '[]')
  } catch {
    return []
  }
}

const getUserOptions = (field: any) => {
  const options = getFieldOptions(field)
  if (options.length > 0) return options
  const selectedIds = Array.isArray(field.user_ids) ? field.user_ids : []
  if (!selectedIds.length) return systemUserOptions.value
  return systemUserOptions.value.filter((item) => selectedIds.includes(item.value))
}

const loadCascadeData = async (selectedOptions: any[], field: any) => {
  // 级联加载逻辑
  const targetOption = selectedOptions[selectedOptions.length - 1]
  targetOption.loading = true
  
  // 模拟异步加载子选项
  setTimeout(() => {
    targetOption.loading = false
    targetOption.children = [
      { label: '子选项1', value: '1', isLeaf: selectedOptions.length >= 2 },
      { label: '子选项2', value: '2', isLeaf: selectedOptions.length >= 2 }
    ]
  }, 500)
}

const handleReferenceSearch = async (keyword: string, field: any) => {
  if (!field.reference_model_id) return
  
  try {
    const res = await getInstances({
      model_id: field.reference_model_id,
      keyword: keyword,
      per_page: 20
    })
    if (res.code === 200) {
      referenceOptions.value[field.id] = res.data.items.map((item: any) => ({
        id: item.id,
        name: item.name
      }))
    }
  } catch (error) {
    console.error(error)
  }
}

const getFileList = (fieldCode: string) => {
  const value = formState.attribute_values[fieldCode]
  if (!value) return []
  if (typeof value === 'string') {
    return [{ uid: value, name: value.split('/').pop(), status: 'done', url: value }]
  }
  return value
}

const handleUpload = async (options: any, field: any) => {
  const { file, onSuccess, onError } = options
  
  try {
    const res = await uploadFile(file)
    if (res.code === 200) {
      formState.attribute_values[field.code] = res.data.url
      onSuccess(res.data)
      message.success('上传成功')
    }
  } catch (error) {
    onError(error)
    message.error('上传失败')
  }
}

const handleRemoveFile = (file: any, field: any) => {
  formState.attribute_values[field.code] = null
}

const handleOk = async () => {
  try {
    await formRef.value.validate()
    loading.value = true
    
    const attributeValues = { ...formState.attribute_values }
    for (const key in attributeValues) {
      if (dayjs.isDayjs(attributeValues[key])) {
        attributeValues[key] = attributeValues[key].format('YYYY-MM-DD HH:mm:ss')
      }
    }
    
    const data = {
      model_id: props.modelId,
      department_id: formState.department_id,
      attribute_values: attributeValues
    }
    
    if (isEdit.value) {
      await updateInstance(formState.id!, data)
      message.success('更新成功')
    } else {
      await createInstance(data)
      message.success('创建成功')
    }
    
    visible.value = false
    emit('success')
  } catch (error: any) {
    message.error(error.response?.data?.message || '操作失败')
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  visible.value = false
}
</script>

<style scoped>
:deep(.ant-divider-horizontal.ant-divider-with-text) {
  margin: 16px 0;
}

.field-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-group-card {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.field-group-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 8px;
}
</style>
