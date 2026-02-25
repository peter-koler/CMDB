<template>
  <div class="template-form">
    <a-form
      :model="formData"
      :rules="formRules"
      layout="vertical"
      @finish="handleSubmit"
    >
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item :label="t('template.form.app')" name="app">
            <a-input
              v-model:value="formData.app"
              :placeholder="t('template.form.appPlaceholder')"
              :disabled="mode === 'edit'"
            />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item :label="t('template.form.category')" name="category">
            <a-select
              v-model:value="formData.category"
              :placeholder="t('template.form.categoryPlaceholder')"
            >
              <a-select-option value="db">{{ t('template.categoryDb') }}</a-select-option>
              <a-select-option value="service">{{ t('template.categoryService') }}</a-select-option>
              <a-select-option value="os">{{ t('template.categoryOs') }}</a-select-option>
              <a-select-option value="middleware">{{ t('template.categoryMiddleware') }}</a-select-option>
              <a-select-option value="custom">{{ t('template.categoryCustom') }}</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item :label="t('template.form.nameZh')" name="nameZh">
            <a-input
              v-model:value="formData.nameZh"
              :placeholder="t('template.form.nameZhPlaceholder')"
            />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item :label="t('template.form.nameEn')" name="nameEn">
            <a-input
              v-model:value="formData.nameEn"
              :placeholder="t('template.form.nameEnPlaceholder')"
            />
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item :label="t('template.form.protocol')" name="protocol">
        <a-select
          v-model:value="formData.protocol"
          :placeholder="t('template.form.protocolPlaceholder')"
        >
          <a-select-option value="http">HTTP</a-select-option>
          <a-select-option value="jdbc">JDBC</a-select-option>
          <a-select-option value="ssh">SSH</a-select-option>
          <a-select-option value="snmp">SNMP</a-select-option>
          <a-select-option value="jmx">JMX</a-select-option>
          <a-select-option value="telnet">Telnet</a-select-option>
          <a-select-option value="custom">{{ t('template.categoryCustom') }}</a-select-option>
        </a-select>
      </a-form-item>

      <!-- 参数配置 -->
      <a-divider>{{ t('template.form.paramsConfig') }}</a-divider>
      <div class="params-section">
        <div class="section-header">
          <span>{{ t('template.form.params') }}</span>
          <a-button type="dashed" size="small" @click="addParam">
            <PlusOutlined />
            {{ t('template.form.addParam') }}
          </a-button>
        </div>
        <div
          v-for="(param, index) in formData.params"
          :key="index"
          class="param-item"
        >
          <a-row :gutter="8">
            <a-col :span="6">
              <a-input
                v-model:value="param.field"
                :placeholder="t('template.form.paramField')"
              />
            </a-col>
            <a-col :span="6">
              <a-input
                v-model:value="param.nameZh"
                :placeholder="t('template.form.paramNameZh')"
              />
            </a-col>
            <a-col :span="5">
              <a-select
                v-model:value="param.type"
                :placeholder="t('template.form.paramType')"
              >
                <a-select-option value="text">Text</a-select-option>
                <a-select-option value="number">Number</a-select-option>
                <a-select-option value="password">Password</a-select-option>
                <a-select-option value="host">Host</a-select-option>
                <a-select-option value="boolean">Boolean</a-select-option>
              </a-select>
            </a-col>
            <a-col :span="5">
              <a-checkbox v-model:checked="param.required">
                {{ t('template.form.required') }}
              </a-checkbox>
            </a-col>
            <a-col :span="2">
              <a-button
                type="link"
                danger
                size="small"
                @click="removeParam(index)"
              >
                <DeleteOutlined />
              </a-button>
            </a-col>
          </a-row>
        </div>
      </div>

      <!-- 指标配置 -->
      <a-divider>{{ t('template.form.metricsConfig') }}</a-divider>
      <div class="metrics-section">
        <div class="section-header">
          <span>{{ t('template.form.metrics') }}</span>
          <a-button type="dashed" size="small" @click="addMetric">
            <PlusOutlined />
            {{ t('template.form.addMetric') }}
          </a-button>
        </div>
        <a-collapse v-model:activeKey="activeMetricKeys">
          <a-collapse-panel
            v-for="(metric, index) in formData.metrics"
            :key="index"
            :header="metric.name || `${t('template.form.metric')} ${index + 1}`"
          >
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item :label="t('template.form.metricName')">
                  <a-input v-model:value="metric.name" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item :label="t('template.form.metricPriority')">
                  <a-input-number
                    v-model:value="metric.priority"
                    :min="0"
                    :max="127"
                    style="width: 100%"
                  />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item :label="t('template.form.metricFields')">
              <div
                v-for="(field, fieldIndex) in metric.fields"
                :key="fieldIndex"
                class="metric-field-item"
              >
                <a-row :gutter="8">
                  <a-col :span="6">
                    <a-input
                      v-model:value="field.field"
                      :placeholder="t('template.form.fieldName')"
                    />
                  </a-col>
                  <a-col :span="5">
                    <a-select v-model:value="field.type" :placeholder="t('template.form.fieldType')">
                      <a-select-option :value="0">Number</a-select-option>
                      <a-select-option :value="1">String</a-select-option>
                    </a-select>
                  </a-col>
                  <a-col :span="5">
                    <a-input
                      v-model:value="field.unit"
                      :placeholder="t('template.form.fieldUnit')"
                    />
                  </a-col>
                  <a-col :span="6">
                    <a-input
                      v-model:value="field.nameZh"
                      :placeholder="t('template.form.fieldNameZh')"
                    />
                  </a-col>
                  <a-col :span="2">
                    <a-button
                      type="link"
                      danger
                      size="small"
                      @click="removeMetricField(index, fieldIndex)"
                    >
                      <DeleteOutlined />
                    </a-button>
                  </a-col>
                </a-row>
              </div>
              <a-button type="dashed" size="small" @click="addMetricField(index)">
                <PlusOutlined />
                {{ t('template.form.addField') }}
              </a-button>
            </a-form-item>
            <a-button
              type="link"
              danger
              @click="removeMetric(index)"
            >
              {{ t('template.form.deleteMetric') }}
            </a-button>
          </a-collapse-panel>
        </a-collapse>
      </div>

      <a-form-item class="form-actions">
        <a-space>
          <a-button type="primary" html-type="submit" :loading="submitting">
            {{ t('common.save') }}
          </a-button>
          <a-button @click="handleCancel">
            {{ t('common.cancel') }}
          </a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const { t } = useI18n()

const props = defineProps<{
  template: any
  mode: 'add' | 'edit'
}>()

const emit = defineEmits<{
  save: [values: any]
  cancel: []
}>()

const submitting = ref(false)
const activeMetricKeys = ref<number[]>([0])

const formData = reactive({
  app: '',
  category: 'service',
  nameZh: '',
  nameEn: '',
  protocol: 'http',
  params: [] as any[],
  metrics: [] as any[]
})

const formRules = {
  app: [{ required: true, message: t('template.form.appRequired') }],
  category: [{ required: true, message: t('template.form.categoryRequired') }],
  nameZh: [{ required: true, message: t('template.form.nameZhRequired') }],
  protocol: [{ required: true, message: t('template.form.protocolRequired') }]
}

// 初始化数据
watch(() => props.template, (val) => {
  if (val) {
    formData.app = val.app || ''
    formData.category = val.category || 'service'
    formData.nameZh = val.name?.['zh-CN'] || ''
    formData.nameEn = val.name?.['en-US'] || ''
    formData.protocol = val.protocol || 'http'
    formData.params = val.params || []
    formData.metrics = val.metrics || []
  } else {
    formData.app = ''
    formData.category = 'service'
    formData.nameZh = ''
    formData.nameEn = ''
    formData.protocol = 'http'
    formData.params = []
    formData.metrics = []
  }
}, { immediate: true })

// 添加参数
const addParam = () => {
  formData.params.push({
    field: '',
    nameZh: '',
    type: 'text',
    required: false
  })
}

// 删除参数
const removeParam = (index: number) => {
  formData.params.splice(index, 1)
}

// 添加指标组
const addMetric = () => {
  const newIndex = formData.metrics.length
  formData.metrics.push({
    name: '',
    priority: 0,
    fields: []
  })
  activeMetricKeys.value.push(newIndex)
}

// 删除指标组
const removeMetric = (index: number) => {
  formData.metrics.splice(index, 1)
}

// 添加指标字段
const addMetricField = (metricIndex: number) => {
  formData.metrics[metricIndex].fields.push({
    field: '',
    type: 0,
    unit: '',
    nameZh: ''
  })
}

// 删除指标字段
const removeMetricField = (metricIndex: number, fieldIndex: number) => {
  formData.metrics[metricIndex].fields.splice(fieldIndex, 1)
}

// 提交
const handleSubmit = async () => {
  submitting.value = true
  try {
    const values = {
      ...formData,
      name: {
        'zh-CN': formData.nameZh,
        'en-US': formData.nameEn
      }
    }
    emit('save', values)
  } finally {
    submitting.value = false
  }
}

// 取消
const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped lang="scss">
.template-form {
  max-height: 600px;
  overflow-y: auto;
  padding-right: 16px;

  .params-section,
  .metrics-section {
    margin-bottom: 24px;

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      font-weight: 500;
    }
  }

  .param-item {
    margin-bottom: 8px;
    padding: 8px;
    background: #f5f5f5;
    border-radius: 4px;
  }

  .metric-field-item {
    margin-bottom: 8px;
  }

  .form-actions {
    margin-top: 24px;
    margin-bottom: 0;
    text-align: right;
  }
}
</style>
