<template>
  <div class="template-view">
    <a-descriptions :title="t('template.view.basicInfo')" bordered>
      <a-descriptions-item :label="t('template.app')">
        {{ template?.app }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('template.category')">
        <a-tag :color="getCategoryColor(template?.category)">
          {{ getCategoryText(template?.category) }}
        </a-tag>
      </a-descriptions-item>
      <a-descriptions-item :label="t('template.protocol')">
        {{ template?.protocol?.toUpperCase() }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('template.name')" :span="2">
        {{ template?.name?.[locale] }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('common.status')">
        <a-tag :color="template?.status === 'active' ? 'success' : 'default'">
          {{ template?.status === 'active' ? t('common.active') : t('common.inactive') }}
        </a-tag>
      </a-descriptions-item>
    </a-descriptions>

    <a-divider />

    <div class="section-title">{{ t('template.view.params') }}</div>
    <a-table
      :columns="paramColumns"
      :data-source="template?.params"
      :pagination="false"
      size="small"
    />

    <a-divider />

    <div class="section-title">{{ t('template.view.metrics') }}</div>
    <a-collapse>
      <a-collapse-panel
        v-for="(metric, index) in template?.metrics"
        :key="index"
        :header="`${metric.name} (${t('template.view.priority')}: ${metric.priority})`"
      >
        <a-table
          :columns="metricFieldColumns"
          :data-source="metric.fields"
          :pagination="false"
          size="small"
        />
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

defineProps<{
  template: any
}>()

const paramColumns = [
  {
    title: t('template.view.paramField'),
    dataIndex: 'field',
    key: 'field'
  },
  {
    title: t('template.view.paramName'),
    dataIndex: 'nameZh',
    key: 'nameZh'
  },
  {
    title: t('template.view.paramType'),
    dataIndex: 'type',
    key: 'type'
  },
  {
    title: t('template.view.required'),
    dataIndex: 'required',
    key: 'required',
    customRender: ({ text }: { text: boolean }) => text ? t('common.yes') : t('common.no')
  }
]

const metricFieldColumns = [
  {
    title: t('template.view.fieldName'),
    dataIndex: 'field',
    key: 'field'
  },
  {
    title: t('template.view.fieldType'),
    dataIndex: 'type',
    key: 'type',
    customRender: ({ text }: { text: number }) => text === 0 ? 'Number' : 'String'
  },
  {
    title: t('template.view.fieldUnit'),
    dataIndex: 'unit',
    key: 'unit'
  },
  {
    title: t('template.view.fieldDisplayName'),
    dataIndex: 'nameZh',
    key: 'nameZh'
  }
]

const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    db: 'blue',
    service: 'green',
    os: 'orange',
    middleware: 'purple',
    custom: 'default'
  }
  return colors[category] || 'default'
}

const getCategoryText = (category: string) => {
  const texts: Record<string, string> = {
    db: t('template.categoryDb'),
    service: t('template.categoryService'),
    os: t('template.categoryOs'),
    middleware: t('template.categoryMiddleware'),
    custom: t('template.categoryCustom')
  }
  return texts[category] || category
}
</script>

<style scoped lang="scss">
.template-view {
  .section-title {
    font-weight: 500;
    margin-bottom: 16px;
    font-size: 16px;
  }
}
</style>
