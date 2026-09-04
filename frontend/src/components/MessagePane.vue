<script setup>
import { nextTick, ref, watch } from 'vue'
import { listMessages, sendMessage } from '../api.js'

const PAGE = 50

const props = defineProps({
  sessionId: { type: [Number, String], required: true },
  hitMessageId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['sent'])

const paneEl = ref(null)
const messages = ref([])
const truncated = ref(false)
const error = ref('')
const expanded = ref(new Set())
const loadingOlder = ref(false)
const hasMore = ref(true)
const sending = ref(false)
let loadPromise = null

function numericIds() {
  return messages.value.map((m) => m.id).filter((id) => Number.isInteger(id))
}

function scrollToBottom() {
  const el = paneEl.value
  if (el) el.scrollTop = el.scrollHeight
}

function sameId(a, b) {
  return a != null && b != null && String(a) === String(b)
}

async function ensureHitVisible(hitId) {
  if (!hitId) return
  while (!messages.value.some((m) => sameId(m.id, hitId)) && hasMore.value) {
    await loadOlder()
  }
  await nextTick()
  document.getElementById('msg-' + hitId)?.scrollIntoView()
}

async function loadLatest({ toBottom = true, scrollToHit = false } = {}) {
  const data = await listMessages(props.sessionId, { limit: PAGE })
  messages.value = data.messages || []
  hasMore.value = (data.messages || []).length >= PAGE
  await nextTick()
  if (scrollToHit && props.hitMessageId) {
    await ensureHitVisible(props.hitMessageId)
  } else if (toBottom) {
    scrollToBottom()
  }
}

async function loadOlder() {
  if (loadingOlder.value || !hasMore.value) return
  const ids = numericIds()
  if (!ids.length) return
  loadingOlder.value = true
  const el = paneEl.value
  const oldHeight = el ? el.scrollHeight : 0
  try {
    const minId = Math.min(...ids)
    const data = await listMessages(props.sessionId, { beforeId: minId, limit: PAGE })
    const older = data.messages || []
    if (older.length < PAGE) hasMore.value = false
    if (older.length) {
      messages.value = [...older, ...messages.value]
      await nextTick()
      if (el) el.scrollTop = el.scrollHeight - oldHeight
    } else {
      hasMore.value = false
    }
  } finally {
    loadingOlder.value = false
  }
}

function onScroll() {
  if (paneEl.value && paneEl.value.scrollTop < 48) loadOlder()
}

function toggleReasoning(id) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

async function send({ content, files, modelId }) {
  if (loadPromise) await loadPromise
  if (sending.value) return
  sending.value = true
  error.value = ''
  truncated.value = false

  const userBubble = {
    id: 'pending-user',
    role: 'user',
    content,
    reasoning: null,
    attachments: files ? [...files].map((f) => ({ original_filename: f.name })) : [],
  }
  const asst = {
    id: 'pending-asst',
    role: 'assistant',
    content: '',
    reasoning: '',
    attachments: [],
  }
  messages.value = [...messages.value, userBubble, asst]
  const liveUser = messages.value[messages.value.length - 2]
  const liveAsst = messages.value[messages.value.length - 1]
  await nextTick()
  scrollToBottom()

  let httpError = false
  let streamError = false
  let gotDone = false
  try {
    await sendMessage({
      sessionId: props.sessionId,
      content,
      modelId,
      files,
      onDelta: (data) => {
        liveAsst.content += data?.text || ''
      },
      onReasoning: (data) => {
        liveAsst.reasoning += data?.text || ''
      },
      onTruncated: () => {
        truncated.value = true
      },
      onDone: () => {
        gotDone = true
      },
      onError: (msg, meta) => {
        error.value = msg || '生成失败'
        if (meta?.http) httpError = true
        else streamError = true
      },
    })

    if (httpError) {
      messages.value = messages.value.filter((m) => m !== liveUser && m !== liveAsst)
    } else if (streamError || !gotDone) {
      messages.value = messages.value.filter((m) => m !== liveAsst)
      if (!gotDone && !streamError) error.value = error.value || '生成失败'
    } else {
      await loadLatest({ toBottom: true })
      emit('sent')
    }
  } catch (e) {
    error.value = e.message || '发送失败'
    messages.value = messages.value.filter((m) => m !== liveAsst)
  } finally {
    sending.value = false
  }
}

watch(
  () => props.sessionId,
  (id) => {
    truncated.value = false
    error.value = ''
    expanded.value = new Set()
    if (id) {
      loadPromise = loadLatest({ toBottom: !props.hitMessageId, scrollToHit: !!props.hitMessageId })
    }
  },
  { immediate: true },
)

watch(
  () => props.hitMessageId,
  (id) => {
    if (id) ensureHitVisible(id)
  },
)

defineExpose({ send })
</script>

<template>
  <div ref="paneEl" class="message-pane" @scroll="onScroll">
    <div v-if="truncated" class="truncation-banner">上下文过长，已截断较早消息</div>
    <div v-if="error" class="chat-error">{{ error }}</div>
    <div
      v-for="m in messages"
      :id="'msg-' + m.id"
      :key="m.id"
      class="msg"
      :class="m.role"
    >
      <div class="msg-content">{{ m.content }}</div>
      <ul v-if="m.attachments && m.attachments.length" class="msg-attachments">
        <li v-for="(a, i) in m.attachments" :key="a.id || i">{{ a.original_filename }}</li>
      </ul>
      <div v-if="m.role === 'assistant' && m.reasoning" class="reasoning">
        <button type="button" @click="toggleReasoning(m.id)">查看推理</button>
        <pre v-show="expanded.has(m.id)">{{ m.reasoning }}</pre>
      </div>
    </div>
  </div>
</template>
