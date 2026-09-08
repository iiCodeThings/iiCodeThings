<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { acceptAttr } from '../api.js'
import { shouldSendOnKeydown } from '../composerKeys.js'
import { parseNewSessionCommand } from '../newSessionCommand.js'
import {
  completeSlashCommand,
  matchSlashCommands,
  parseSearchCommand,
  slashCommandDraft,
} from '../slashCommands.js'
import Icon from './Icons.vue'

const props = defineProps({
  modelId: { type: [Number, String, null], default: null },
  sessionId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['send'])

const content = ref('')
const files = ref(null)
const fileInput = ref(null)
const enableThinking = ref(false)
const suppressSuggest = ref(false)
const highlight = ref(0)

const fileNames = computed(() => {
  const list = files.value
  if (!list || !list.length) return []
  return [...list].map((f) => f.name)
})

const slashMatches = computed(() => {
  if (suppressSuggest.value) return []
  return matchSlashCommands(slashCommandDraft(content.value))
})

const slashOpen = computed(() => slashMatches.value.length > 0)

watch(content, () => {
  suppressSuggest.value = false
})

watch(slashMatches, () => {
  highlight.value = 0
})

function applySlash(command) {
  content.value = completeSlashCommand(command)
  suppressSuggest.value = true
}

function onFileChange(e) {
  files.value = e.target.files
}

function onSend() {
  const text = content.value
  if (parseNewSessionCommand(text) || parseSearchCommand(text)) {
    emit('send', { content: text, files: [], enableThinking: enableThinking.value })
    content.value = ''
    files.value = null
    if (fileInput.value) fileInput.value.value = ''
    return
  }
  if (!props.modelId) {
    alert('请先在设置中添加模型')
    return
  }
  const fileList = files.value
  if (!text.trim() && (!fileList || fileList.length === 0)) return
  const snapshot = fileList ? [...fileList] : []
  emit('send', { content: text, files: snapshot, enableThinking: enableThinking.value })
  content.value = ''
  files.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function onKeydown(e) {
  if (slashOpen.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      highlight.value = Math.min(slashMatches.value.length - 1, highlight.value + 1)
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      highlight.value = Math.max(0, highlight.value - 1)
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      const row = slashMatches.value[highlight.value]
      if (row) applySlash(row.command)
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      suppressSuggest.value = true
      return
    }
  }
  if (!shouldSendOnKeydown(e)) return
  e.preventDefault()
  onSend()
}

function onDocPointer(e) {
  if (!slashOpen.value) return
  const el = e.target
  if (el && typeof el.closest === 'function' && el.closest('.composer')) return
  suppressSuggest.value = true
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocPointer)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointer)
})

defineExpose({ content, files, onSend })
</script>

<template>
  <div class="composer">
    <div class="composer-box">
      <ul
        v-if="slashOpen"
        class="slash-suggest"
        role="listbox"
        aria-label="斜杠命令"
      >
        <li
          v-for="(row, i) in slashMatches"
          :key="row.id"
          role="option"
          :aria-selected="i === highlight"
          :class="{ active: i === highlight }"
        >
          <button
            type="button"
            @mousedown.prevent
            @click="applySlash(row.command)"
          >
            <span class="slash-cmd">{{ row.command }}</span>
            <span class="slash-hint">{{ row.hint }}</span>
          </button>
        </li>
      </ul>
      <textarea
        v-model="content"
        rows="2"
        placeholder="输入消息…"
        aria-label="消息输入"
        :aria-expanded="slashOpen ? 'true' : 'false'"
        @keydown="onKeydown"
      />
      <ul v-if="fileNames.length" class="file-chips">
        <li v-for="name in fileNames" :key="name">{{ name }}</li>
      </ul>
      <div class="composer-actions">
        <div class="composer-actions-left">
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
          <label class="think-toggle">
            <input v-model="enableThinking" type="checkbox" name="enable_thinking" />
            推理
          </label>
        </div>
        <button type="button" class="send-btn" @click="onSend">发送</button>
      </div>
    </div>
  </div>
</template>
