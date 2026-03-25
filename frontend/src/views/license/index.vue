<template>
  <div class="app-page license-page">
    <a-card title="License 授权管理" :bordered="false" class="app-surface-card">
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="机器码">{{ status.machine_code || '-' }}</a-descriptions-item>
        <a-descriptions-item label="授权状态">{{ status.has_license ? (status.expired ? '已过期' : '有效') : '未授权' }}</a-descriptions-item>
        <a-descriptions-item label="到期时间">{{ status.expire_time || '-' }}</a-descriptions-item>
        <a-descriptions-item label="监控上限">{{ status.max_monitors || 0 }}</a-descriptions-item>
        <a-descriptions-item label="已启用监控">{{ status.enabled_monitors || 0 }}</a-descriptions-item>
        <a-descriptions-item label="防回拨状态">{{ status.halted ? '已停止采集' : '正常' }}</a-descriptions-item>
        <a-descriptions-item v-if="status.halt_reason" label="停止原因">{{ status.halt_reason }}</a-descriptions-item>
      </a-descriptions>

      <div class="upload-box">
        <a-upload
          :before-upload="beforeUpload"
          :show-upload-list="false"
          accept=".lic,.txt,.json"
        >
          <a-button type="primary" :loading="uploading">上传 License 文件</a-button>
        </a-upload>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message, Upload } from 'ant-design-vue'
import type { UploadProps } from 'ant-design-vue'
import { getLicenseStatus, uploadLicense, type LicenseStatus } from '@/api/license'

const uploading = ref(false)
const status = reactive<LicenseStatus>({
  has_license: false,
  expired: false,
  machine_code: '',
  max_monitors: 0,
  enabled_monitors: 0,
  halted: false
})

const loadStatus = async () => {
  try {
    const resp = await getLicenseStatus()
    Object.assign(status, resp.data || {})
  } catch (error: any) {
    message.error(error?.response?.data?.message || '获取 license 状态失败')
  }
}

const beforeUpload: UploadProps['beforeUpload'] = async (file) => {
  uploading.value = true
  try {
    const text = await file.text()
    await uploadLicense(text)
    message.success('License 上传成功')
    await loadStatus()
  } catch (error: any) {
    message.error(error?.response?.data?.message || 'License 上传失败')
  } finally {
    uploading.value = false
  }
  return Upload.LIST_IGNORE
}

onMounted(() => {
  loadStatus()
})
</script>

<style scoped>
.license-page {
  min-height: 100%;
}

.upload-box {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--arco-border);
}
</style>
