import request from '@/utils/request'

export function getModelTriggers(modelId: number) {
  return request.get(`/models/${modelId}/triggers`)
}

export function createTrigger(modelId: number, data: any) {
  return request.post(`/models/${modelId}/triggers`, data)
}

export function getTrigger(triggerId: number) {
  return request.get(`/triggers/${triggerId}`)
}

export function updateTrigger(triggerId: number, data: any) {
  return request.put(`/triggers/${triggerId}`, data)
}

export function deleteTrigger(triggerId: number) {
  return request.delete(`/triggers/${triggerId}`)
}

export function getTriggerLogs(triggerId: number, params?: any) {
  return request.get(`/triggers/${triggerId}/logs`, { params })
}

export function triggerBatchScan(modelId: number) {
  return request.post(`/models/${modelId}/batch-scan`)
}

export function getModelBatchScanTasks(modelId: number, params?: any) {
  return request.get(`/models/${modelId}/batch-scan`, { params })
}

export function getAllBatchScanTasks(params?: any) {
  return request.get('/batch-scan/tasks', { params })
}

export function getBatchScanTask(taskId: number) {
  return request.get(`/batch-scan/tasks/${taskId}`)
}

export function getBatchScanConfig(modelId: number) {
  return request.get(`/batch-scan/config/${modelId}`)
}

export function updateBatchScanConfig(modelId: number, data: any) {
  return request.put(`/batch-scan/config/${modelId}`, data)
}
