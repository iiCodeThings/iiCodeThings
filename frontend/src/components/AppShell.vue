<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import Composer from './Composer.vue'
import { createSession, listModels, listSessions } from '../api.js'

const route = useRoute()
const router = useRouter()

const currentId = ref(null)
const sessions = ref([])
const models = ref([])
const search = ref('')
const selectedModelId = ref('')

const filteredSessions = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return sessions.value
  const tokens = q.split(/\s+/).filter(Boolean)
  return sessions.value.filter((s) => {
    const title = (s.title || '').toLowerCase()
    return tokens.every((t) => title.includes(t))
  })
})

const modelId = computed(() =>
  selectedModelId.value === '' ? null : Number(selectedModelId.value),
)

async function loadSessions() {
  sessions.value = await listSessions()
}

async function loadModels() {
  models.value = await listModels()
}

async function onNewChat() {
  const s = await createSession()
  await loadSessions()
  currentId.value = s.id
  if (route.path !== '/') router.push('/')
}

function onSelect(id) {
  currentId.value = id
  if (route.path !== '/') router.push('/')
}

onMounted(async () => {
  try {
    await Promise.all([loadSessions(), loadModels()])
  } catch {
    /* 401 redirects via jsonFetch */
  }
})

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
            v-for="s in filteredSessions"
            :key="s.id"
            :class="{ active: currentId === s.id }"
            @click="onSelect(s.id)"
          >
            <span class="session-title">{{ s.title }}</span>
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
      <Composer :model-id="modelId" :session-id="currentId" />
    </aside>
    <main class="right">
      <RouterView :current-id="currentId" :model-id="modelId" />
    </main>
  </div>
</template>
