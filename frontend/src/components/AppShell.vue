<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import Composer from './Composer.vue'
import { createSession, listModels, listSessions, searchSessions } from '../api.js'

const route = useRoute()
const router = useRouter()

const currentId = ref(null)
const hitMessageId = ref(null)
const sessions = ref([])
const models = ref([])
const search = ref('')
const selectedModelId = ref('')
const viewRef = ref(null)
let searchTimer = null

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

async function runSearch(q) {
  const trimmed = q.trim()
  if (!trimmed) {
    await loadSessions()
    return
  }
  const data = await searchSessions(trimmed)
  sessions.value = data.sessions || []
}

async function onNewChat() {
  const s = await createSession()
  await loadSessions()
  currentId.value = s.id
  hitMessageId.value = null
  if (route.path !== '/') router.push('/')
}

function onSelect(s) {
  currentId.value = s.id
  hitMessageId.value = s.hit_message_id ?? null
  if (route.path !== '/') router.push('/')
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
    hitMessageId.value = null
    await nextTick()
  }
  await nextTick()
  await viewRef.value?.send({ content, files, modelId: modelId.value })
}

function onSent() {
  runSearch(search.value).catch(() => {})
}

watch(search, (q) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    runSearch(q).catch(() => {})
  }, 300)
})

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
        <input
          v-model="search"
          class="search"
          type="search"
          placeholder="搜索对话"
          aria-label="搜索对话"
        />
        <button type="button" class="new-chat" @click="onNewChat">新对话</button>
        <ul class="session-list">
          <li
            v-for="s in sessions"
            :key="s.id"
            :class="{ active: currentId === s.id }"
            @click="onSelect(s)"
          >
            <span class="session-title">{{ s.title }}</span>
            <span v-if="s.snippet" class="session-snippet">{{ s.snippet }}</span>
            <span v-if="s.updated_at" class="session-time">{{ s.updated_at }}</span>
          </li>
        </ul>
        <label class="model-select">
          模型
          <select v-model="selectedModelId">
            <option v-for="m in models" :key="m.id" :value="String(m.id)">{{ m.name }}</option>
          </select>
        </label>
        <RouterLink class="settings-link" to="/settings">设置</RouterLink>
      </div>
      <Composer :model-id="modelId" :session-id="currentId" @send="onComposerSend" />
    </aside>
    <main class="right">
      <RouterView v-slot="{ Component }">
        <component
          :is="Component"
          ref="viewRef"
          :current-id="currentId"
          :model-id="modelId"
          :hit-message-id="hitMessageId"
          @sent="onSent"
        />
      </RouterView>
    </main>
  </div>
</template>
