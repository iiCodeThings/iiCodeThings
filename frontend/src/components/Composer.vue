<script setup>
import { computed, ref } from 'vue'
import { acceptAttr } from '../api.js'
import Icon from './Icons.vue'

const props = defineProps({
  modelId: { type: [Number, String, null], default: null },
  sessionId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['send'])

const content = ref('')
const files = ref(null)
const fileInput = ref(null)

const fileNames = computed(() => {
  const list = files.value
  if (!list || !list.length) return []
  return [...list].map((f) => f.name)
})

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
  const snapshot = fileList ? [...fileList] : []
  emit('send', { content: text, files: snapshot })
  content.value = ''
  files.value = null
  if (fileInput.value) fileInput.value.value = ''
}

defineExpose({ content, files, onSend })
</script>

<template>
  <div class="composer">
    <div class="composer-box">
      <textarea
        v-model="content"
        rows="3"
        placeholder="输入消息…"
        aria-label="消息输入"
      />
      <ul v-if="fileNames.length" class="file-chips">
        <li v-for="name in fileNames" :key="name">{{ name }}</li>
      </ul>
      <div class="composer-actions">
        <label class="icon-btn attach" title="添加附件">
          <Icon name="clip" />
          <span class="sr-only">添加附件</span>
          <input
            ref="fileInput"
            type="file"
            multiple
            :accept="acceptAttr"
            @change="onFileChange"
          />
        </label>
        <button type="button" class="send-btn" @click="onSend">发送</button>
      </div>
    </div>
  </div>
</template>
