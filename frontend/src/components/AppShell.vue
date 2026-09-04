<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { createSession, deleteSession, listModels, listSessions, patchSession } from '../api.js'
import Icon from './Icons.vue'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const route = useRoute()
const router = useRouter()

const currentId = ref(null)
const sessions = ref([])
const models = ref([])
const selectedModelId = ref('')
const viewRef = ref(null)

const modelId = computed(() =>
  selectedModelId.value === '' ? null : Number(selectedModelId.value),
)

async function loadSessions() {
  sessions.value = await listSessions()
}

async function loadModels() {
  models.value = await listModels()
  const ids = models.value.map((m) => String(m.id))
  if (models.value.length === 0) {
    selectedModelId.value = ''
    return
  }
  if (!selectedModelId.value || !ids.includes(selectedModelId.value)) {
    selectedModelId.value = String(models.value[0].id)
  }
}

async function onNewChat() {
  const s = await createSession()
  await loadSessions()
  currentId.value = s.id
  if (route.path !== '/') router.push('/')
}

function onSelect(s) {
  currentId.value = s.id
  if (route.path !== '/') router.push('/')
}

async function onRename(s, ev) {
  ev.stopPropagation()
  const next = window.prompt('重命名会话', s.title)
  if (next == null) return
  const title = next.trim()
  if (!title) return
  await patchSession(s.id, title)
  await loadSessions()
}

async function onDelete(s, ev) {
  ev.stopPropagation()
  if (!window.confirm(`删除会话「${s.title}」？`)) return
  await deleteSession(s.id)
  if (currentId.value === s.id) {
    currentId.value = null
  }
  await loadSessions()
}

async function onComposerSend({ content, files }) {
  if (!modelId.value) {
    alert('请先在设置中添加模型')
    return
  }
  if (route.path !== '/') {
    await router.push('/')
    await nextTick()
  }
  if (!currentId.value) {
    const s = await createSession()
    await loadSessions()
    currentId.value = s.id
    await nextTick()
  }
  await nextTick()
  await viewRef.value?.send({ content, files, modelId: modelId.value })
}

function onSent() {
  loadSessions().catch(() => {})
}

onMounted(async () => {
  try {
    await Promise.all([loadSessions(), loadModels()])
  } catch {
    /* 401 redirects via jsonFetch */
  }
})

watch(
  () => route.path,
  async (path, prev) => {
    if (prev === '/settings' && path !== '/settings') {
      try {
        await loadModels()
      } catch {
        /* 401 redirects via jsonFetch */
      }
    }
  },
)

defineExpose({ loadSessions, loadModels, currentId, modelId })
</script>

<template>
  <div class="shell">
    <aside class="left">
      <div class="nav">
        <div class="brand">
          <span class="brand-mark" aria-hidden="true"></span>
          <span class="brand-name">对话</span>
        </div>
        <button type="button" class="new-chat" @click="onNewChat">新对话</button>
        <ul class="session-list">
          <li
            v-for="s in sessions"
            :key="s.id"
            :class="{ active: currentId === s.id }"
            @click="onSelect(s)"
          >
            <div class="session-head">
              <span class="session-title">{{ s.title }}</span>
              <span class="session-actions">
                <button type="button" class="icon-btn" title="重命名" aria-label="重命名" @click="onRename(s, $event)">
                  <Icon name="quill" />
                </button>
                <button type="button" class="icon-btn danger" title="删除" aria-label="删除" @click="onDelete(s, $event)">
                  <Icon name="inkx" />
                </button>
              </span>
            </div>
            <span v-if="s.updated_at" class="session-time">{{ formatTime(s.updated_at) }}</span>
          </li>
        </ul>
        <div class="nav-foot">
          <label class="model-select">
            模型
            <select v-model="selectedModelId">
              <option v-for="m in models" :key="m.id" :value="String(m.id)">{{ m.name }}</option>
            </select>
          </label>
          <RouterLink class="settings-link" to="/settings">设置</RouterLink>
        </div>
      </div>
    </aside>
    <main class="right">
      <RouterView v-slot="{ Component }">
        <component
          :is="Component"
          ref="viewRef"
          :current-id="currentId"
          :model-id="modelId"
          @sent="onSent"
          @compose="onComposerSend"
        />
      </RouterView>
    </main>
  </div>
</template>
