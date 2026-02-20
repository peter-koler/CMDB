<template>
  <div class="rich-editor-container">
    <Toolbar
      class="toolbar"
      :editor="editorRef"
      :default-config="toolbarConfig"
      mode="default"
    />
    <Editor
      v-model="valueHtml"
      class="editor"
      :default-config="editorConfig"
      mode="default"
      @onCreated="handleCreated"
      @onChange="handleChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, onMounted, onBeforeUnmount, watch } from 'vue'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import '@wangeditor/editor/dist/css/style.css'
import { uploadImage } from '@/api/upload'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  height?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorRef = shallowRef()
const valueHtml = ref('')

const toolbarConfig = {
  excludeKeys: [
    'group-video'
  ]
}

const editorConfig = {
  placeholder: props.placeholder || '请输入内容...',
  MENU_CONF: {
    uploadImage: {
      async customUpload(file: File, insertFn: any) {
        try {
          const formData = new FormData()
          formData.append('file', file)
          const res = await uploadImage(formData)
          if (res.code === 200 && res.data?.url) {
            insertFn(res.data.url, file.name, res.data.url)
          }
        } catch (error) {
          console.error('图片上传失败:', error)
        }
      }
    },
    insertImage: {
      parseImageSrc: (src: string) => src
    }
  }
}

watch(
  () => props.modelValue,
  (val) => {
    if (val !== valueHtml.value) {
      valueHtml.value = val
    }
  },
  { immediate: true }
)

const handleCreated = (editor: any) => {
  editorRef.value = editor
}

const handleChange = (editor: any) => {
  emit('update:modelValue', valueHtml.value)
}

onBeforeUnmount(() => {
  const editor = editorRef.value
  if (editor) {
    editor.destroy()
  }
})
</script>

<style scoped>
.rich-editor-container {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
}

.toolbar {
  border-bottom: 1px solid #d9d9d9;
}

.editor {
  height: v-bind('height ? height + "px" : "300px"');
  overflow-y: auto;
}
</style>
