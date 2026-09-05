<script setup>
import { nextTick, ref, watch } from 'vue'
import { listMessages, sendMessage } from '../api.js'
import { renderMarkdown } from '../markdown.js'
import { isAwaitingReply } from '../awaitingReply.js'
import { isNearBottom } from '../paneScroll.js'

const PAGE = 50

const props = defineProps({
  sessionId: { type: [Number, String], required: true },
  hitMessageId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['sent'])

const paneEl = ref(null)
const messages = ref([])
const truncated = ref(false)
const warning = ref('')
const error = ref('')
const expanded = ref(new Set())
const loadingOlder = ref(false)
const hasMore = ref(true)
const sending = ref(false)
const streamingId = ref(null)
const stickToBottom = ref(true)
let loadPromise = null
let loadGen = 0

function numericIds() {
  return messages.value.map((m) => m.id).filter((id) => Number.isInteger(id))
}

function scrollToBottom({ force = false } = {}) {
  const el = paneEl.value
  if (!el) return
  if (!force && !stickToBottom.value) return
  el.scrollTop = el.scrollHeight
}

function sameId(a, b) {
  return a != null && b != null && String(a) === String(b)
}

async function ensureHitVisible(hitId) {
  if (!hitId) return
  const gen = loadGen
  while (!messages.value.some((m) => sameId(m.id, hitId)) && hasMore.value) {
    if (gen !== loadGen) return
    await loadOlder()
  }
  if (gen !== loadGen) return
  await nextTick()
  document.getElementById('msg-' + hitId)?.scrollIntoView()
}

async function loadLatest({ toBottom = true, scrollToHit = false } = {}) {
  const gen = loadGen
  try {
    const data = await listMessages(props.sessionId, { limit: PAGE })
    if (gen !== loadGen) return
    messages.value = data.messages || []
    hasMore.value = (data.messages || []).length >= PAGE
    await nextTick()
    if (gen !== loadGen) return
    if (scrollToHit && props.hitMessageId) {
      await ensureHitVisible(props.hitMessageId)
    } else if (toBottom) {
      stickToBottom.value = true
      scrollToBottom({ force: true })
    }
  } catch (e) {
    if (gen !== loadGen) return
    error.value = error.value || e.message || '加载消息失败'
  }
}

async function loadOlder() {
  if (loadingOlder.value || !hasMore.value) return
  const gen = loadGen
  const ids = numericIds()
  if (!ids.length) return
  loadingOlder.value = true
  const el = paneEl.value
  const oldHeight = el ? el.scrollHeight : 0
  try {
    const minId = Math.min(...ids)
    const data = await listMessages(props.sessionId, { beforeId: minId, limit: PAGE })
    if (gen !== loadGen) return
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
    if (gen === loadGen) loadingOlder.value = false
  }
}

function onScroll() {
  const el = paneEl.value
  if (!el) return
  stickToBottom.value = isNearBottom(el)
  if (el.scrollTop < 48) loadOlder()
}

function toggleReasoning(id) {
  if (streamingId.value != null && sameId(id, streamingId.value)) return
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

function isLive(m) {
  return streamingId.value != null && sameId(m.id, streamingId.value)
}

function reasoningOpen(m) {
  return isLive(m) || expanded.value.has(m.id)
}

function reasoningLabel(m) {
  if (isLive(m)) return '正在推理'
  return reasoningOpen(m) ? '收起推理' : '推理过程'
}

async function send({ content, files, modelId, enableThinking }) {
  if (loadPromise) await loadPromise
  if (sending.value) return
  sending.value = true
  error.value = ''
  truncated.value = false
  warning.value = ''

  const stamp = Date.now()
  const userBubble = {
    id: 'pending-user-' + stamp,
    role: 'user',
    content,
    reasoning: null,
    attachments: files ? [...files].map((f) => ({ original_filename: f.name })) : [],
  }
  const asst = {
    id: 'pending-asst-' + stamp,
    role: 'assistant',
    content: '',
    reasoning: '',
    attachments: [],
  }
  messages.value = [...messages.value, userBubble, asst]
  const liveUser = messages.value[messages.value.length - 2]
  const liveAsst = messages.value[messages.value.length - 1]
  streamingId.value = asst.id
  stickToBottom.value = true
  await nextTick()
  scrollToBottom({ force: true })

  let httpError = false
  let streamError = false
  let gotDone = false
  try {
    await sendMessage({
      sessionId: props.sessionId,
      content,
      modelId,
      files,
      enableThinking: !!enableThinking,
      onDelta: (data) => {
        liveAsst.content += data?.text || ''
        scrollToBottom()
      },
      onReasoning: (data) => {
        liveAsst.reasoning += data?.text || ''
        scrollToBottom()
      },
      onTruncated: () => {
        truncated.value = true
      },
      onWarning: (data) => {
        warning.value = data?.text || '文档未能抽出文字，已保存原文件'
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
      if (!gotDone && !streamError) error.value = error.value || '生成失败'
      await loadLatest({ toBottom: stickToBottom.value })
    } else {
      await loadLatest({ toBottom: stickToBottom.value })
      emit('sent')
    }
  } catch (e) {
    error.value = e.message || '发送失败'
    await loadLatest({ toBottom: stickToBottom.value })
  } finally {
    sending.value = false
    streamingId.value = null
  }
}

watch(
  () => props.sessionId,
  (id) => {
    loadGen += 1
    messages.value = []
    hasMore.value = true
    loadingOlder.value = false
    truncated.value = false
    warning.value = ''
    error.value = ''
    expanded.value = new Set()
    streamingId.value = null
    stickToBottom.value = !props.hitMessageId
    if (id) {
      loadPromise = loadLatest({ toBottom: !props.hitMessageId, scrollToHit: !!props.hitMessageId })
    }
  },
  { immediate: true },
)

watch(
  () => props.hitMessageId,
  async (id) => {
    if (!id) return
    if (loadPromise) await loadPromise
    await ensureHitVisible(id)
  },
)

defineExpose({ send })
</script>

<template>
  <div ref="paneEl" class="message-pane" @scroll="onScroll">
    <div v-if="truncated" class="truncation-banner">上下文过长，已截断较早消息</div>
    <div v-if="warning" class="extract-warning">{{ warning }}</div>
    <div v-if="error" class="chat-error">{{ error }}</div>
    <div
      v-for="m in messages"
      :id="'msg-' + m.id"
      :key="m.id"
      class="msg"
      :class="m.role"
    >
      <div v-if="m.role === 'assistant' && m.reasoning" class="reasoning" :class="{ live: isLive(m) }">
        <button
          type="button"
          class="reasoning-toggle"
          :disabled="isLive(m)"
          @click="toggleReasoning(m.id)"
        >
          <span class="reasoning-dot" aria-hidden="true"></span>
          {{ reasoningLabel(m) }}
        </button>
        <div v-show="reasoningOpen(m)" class="reasoning-body">{{ m.reasoning }}</div>
      </div>
      <div v-if="m.model_name" class="msg-model">{{ m.model_name }}</div>
      <div
        v-if="isAwaitingReply({ live: isLive(m), content: m.content, reasoning: m.reasoning })"
        class="msg-waiting"
        aria-live="polite"
      >
        <span class="msg-spinner" aria-hidden="true"></span>
        <span>正在生成</span>
      </div>
      <div v-if="m.content" class="msg-content md" v-html="renderMarkdown(m.content)"></div>
      <ul v-if="m.attachments && m.attachments.length" class="msg-attachments">
        <li v-for="(a, i) in m.attachments" :key="a.id || i">{{ a.original_filename }}</li>
      </ul>
    </div>
  </div>
</template>
