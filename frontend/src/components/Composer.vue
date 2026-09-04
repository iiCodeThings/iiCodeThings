<script setup>
import { ref } from 'vue'
import { acceptAttr } from '../api.js'

const props = defineProps({
  modelId: { type: [Number, String, null], default: null },
  sessionId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['send'])

const content = ref('')
const files = ref(null)
const fileInput = ref(null)

function onFileChange(e) {
  files.value = e.target.files
}

function onSend() {
  if (!props.modelId) {
    alert('请先在设置中添加模型')
    return
  }
  const text = content.value
  const fileList = files.value
  if (!text.trim() && (!fileList || fileList.length === 0)) return
  emit('send', { content: text, files: fileList })
  content.value = ''
  files.value = null
  if (fileInput.value) fileInput.value.value = ''
}

defineExpose({ content, files, onSend })
</script>

<template>
  <div class="composer">
    <textarea
      v-model="content"
      rows="3"
      placeholder="输入消息…"
      aria-label="消息输入"
    />
    <div class="composer-actions">
      <input
        ref="fileInput"
        type="file"
        multiple
        :accept="acceptAttr"
        @change="onFileChange"
      />
      <button type="button" @click="onSend">发送</button>
    </div>
  </div>
</template>
