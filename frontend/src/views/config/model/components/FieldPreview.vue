<template>
  <div class="field-preview">
    <template v-if="field.field_type === 'text'">
      <a-input :placeholder="field.name" disabled />
    </template>
    <template v-else-if="field.field_type === 'number'">
      <a-input-number :placeholder="field.name" style="width: 100%" disabled />
    </template>
    <template v-else-if="field.field_type === 'select'">
      <a-select :placeholder="field.name" disabled style="width: 100%">
        <a-select-option v-for="opt in field.options" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </a-select-option>
      </a-select>
    </template>
    <template v-else-if="field.field_type === 'multiselect'">
      <a-select :placeholder="field.name" mode="multiple" disabled style="width: 100%">
        <a-select-option v-for="opt in field.options" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </a-select-option>
      </a-select>
    </template>
    <template v-else-if="field.field_type === 'dropdown'">
      <a-select :placeholder="field.name" disabled style="width: 100%">
        <a-select-option v-for="opt in field.options" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </a-select-option>
      </a-select>
    </template>
    <template v-else-if="field.field_type === 'cascade'">
      <a-cascader :placeholder="field.name" disabled style="width: 100%" />
    </template>
    <template v-else-if="field.field_type === 'reference'">
      <a-select :placeholder="field.name" disabled style="width: 100%" />
    </template>
    <template v-else-if="field.field_type === 'file'">
      <a-upload disabled>
        <a-button disabled>
          <UploadOutlined />
          上传附件
        </a-button>
      </a-upload>
    </template>
    <template v-else-if="field.field_type === 'image'">
      <a-upload list-type="picture-card" disabled>
        <div>
          <PlusOutlined />
          <div style="margin-top: 8px">上传图片</div>
        </div>
      </a-upload>
    </template>
    <template v-else-if="field.field_type === 'richtext'">
      <a-textarea :placeholder="field.name" :rows="4" disabled />
    </template>
    <template v-else-if="field.field_type === 'date'">
      <a-date-picker :placeholder="field.name" style="width: 100%" disabled />
    </template>
    <template v-else-if="field.field_type === 'datetime'">
      <a-date-picker show-time :placeholder="field.name" style="width: 100%" disabled />
    </template>
    <template v-else>
      <a-input :placeholder="field.name" disabled />
    </template>
  </div>
</template>

<script setup lang="ts">
import { UploadOutlined, PlusOutlined } from '@ant-design/icons-vue'

defineProps<{
  field: any
}>()
</script>

<style scoped>
.field-preview {
  width: 100%;
}
</style>
