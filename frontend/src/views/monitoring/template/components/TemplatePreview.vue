<template>
  <div class="template-preview">
    <a-descriptions :title="t('template.preview.basicInfo')" bordered :column="2">
      <a-descriptions-item :label="t('template.app')">
        {{ parsedConfig.app }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('template.category')">
        {{ parsedConfig.category }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('template.name')" :span="2">
        {{ parsedConfig.name?.['zh-CN'] }} / {{ parsedConfig.name?.['en-US'] }}
      </a-descriptions-item>
    </a-descriptions>

    <a-divider />

    <div class="section-title">{{ t('template.preview.params') }}</div>
    <a-table
      :columns="paramColumns"
      :data-source="parsedConfig.params"
      :pagination="false"
      size="small"
      bordered
    />

    <a-divider />

    <div class="section-title">{{ t('template.preview.metrics') }}</div>
    <a-collapse v-if="parsedConfig.metrics?.length > 0">
      <a-collapse-panel
        v-for="(metric, index) in parsedConfig.metrics"
        :key="index"
        :header="`${metric.name} (${t('template.preview.priority')}: ${metric.priority})`"
      >
        <a-descriptions size="small" :column="2">
          <a-descriptions-item :label="t('template.preview.protocol')">
            {{ metric.protocol }}
          </a-descriptions-item>
          <a-descriptions-item :label="t('template.preview.priority')">
            {{ metric.priority }}
          </a-descriptions-item>
        </a-descriptions>
        
        <div class="fields-title">{{ t('template.preview.fields') }}</div>
        <a-table
          :columns="fieldColumns"
          :data-source="metric.fields"
          :pagination="false"
          size="small"
          bordered
        />
      </a-collapse-panel>
    </a-collapse>
    <a-empty v-else :description="t('template.preview.noMetrics')" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import * as yaml from 'js-yaml'

const { t } = useI18n()
const pt = (key: string) => t(`template.previewDetail.${key}`)

const props = defineProps<{
  yamlContent: string
}>()

const parsedConfig = computed(() => {
  try {
    return yaml.load(props.yamlContent) || {}
  } catch (e) {
    console.error('YAML parse error:', e)
    return {}
  }
})

const paramColumns = [
  {
    title: pt('paramField'),
    dataIndex: 'field',
    key: 'field',
    width: 150
  },
  {
    title: pt('paramName'),
    key: 'name',
    customRender: ({ record }: { record: any }) => {
      return record.name?.['zh-CN'] || record.name?.['en-US'] || record.field
    }
  },
  {
    title: pt('paramType'),
    dataIndex: 'type',
    key: 'type',
    width: 100
  },
  {
    title: pt('required'),
    dataIndex: 'required',
    key: 'required',
    width: 80,
    customRender: ({ text }: { text: boolean }) => text ? t('common.yes') : t('common.no')
  },
  {
    title: pt('defaultValue'),
    dataIndex: 'defaultValue',
    key: 'defaultValue',
    width: 120
  }
]

const fieldColumns = [
  {
    title: pt('fieldName'),
    dataIndex: 'field',
    key: 'field',
    width: 150
  },
  {
    title: pt('fieldType'),
    dataIndex: 'type',
    key: 'type',
    width: 100,
    customRender: ({ text }: { text: number }) => text === 0 ? 'Number' : 'String'
  },
  {
    title: pt('fieldUnit'),
    dataIndex: 'unit',
    key: 'unit',
    width: 100
  },
  {
    title: pt('fieldLabel'),
    dataIndex: 'label',
    key: 'label',
    width: 100,
    customRender: ({ text }: { text: boolean }) => text ? t('common.yes') : t('common.no')
  }
]
</script>

<style scoped lang="scss">
.template-preview {
  max-height: 600px;
  overflow-y: auto;

  .section-title {
    font-weight: 500;
    margin-bottom: 16px;
    font-size: 16px;
  }

  .fields-title {
    font-weight: 500;
    margin: 16px 0 8px 0;
  }
}
</style>
