<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  createSession,
  deleteSession,
  listModels,
  listSessions,
  patchSession,
  pinSession,
  retitleSession,
  shareSession,
  unpinSession,
} from '../api.js'
import { NARROW_QUERY, nextDrawerOpen, sessionActionsMode } from '../layout.js'
import { explainRetitleResult } from '../retitleFeedback.js'
import { copySharePath } from '../shareLink.js'
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
const retitlingId = ref(null)
const narrow = ref(false)
const drawerOpen = ref(false)
const menuOpenId = ref(null)

const modelId = computed(() =>
  selectedModelId.value === '' ? null : Number(selectedModelId.value),
)

const currentTitle = computed(() => {
  const row = sessions.value.find((s) => s.id === currentId.value)
  return row?.title || '对话'
})

function setDrawer(action) {
  drawerOpen.value = nextDrawerOpen({
    open: drawerOpen.value,
    narrow: narrow.value,
    action,
  })
}

function onHamburger() {
  setDrawer('toggle')
}

function onBackdrop() {
  setDrawer('backdrop')
}

function onDrawerKey(e) {
  if (e.key === 'Escape') {
    setDrawer('escape')
    menuOpenId.value = null
  }
}

function onDocPointer(e) {
  if (menuOpenId.value == null) return
  const el = e.target
  if (el && typeof el.closest === 'function' && el.closest('.session-actions.menu')) return
  menuOpenId.value = null
}

let narrowMq = null

function applyNarrow() {
  if (!narrowMq) return
  narrow.value = narrowMq.matches
  if (!narrowMq.matches) setDrawer('widen')
}

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
  menuOpenId.value = null
  setDrawer('select')
  if (route.path !== '/') router.push('/')
}

function onSelect(s) {
  currentId.value = s.id
  menuOpenId.value = null
  setDrawer('select')
  if (route.path !== '/') router.push('/')
}

async function onPin(s, ev) {
  menuOpenId.value = null
  ev.stopPropagation()
  await pinSession(s.id)
  await loadSessions()
}

async function onUnpin(s, ev) {
  menuOpenId.value = null
  ev.stopPropagation()
  await unpinSession(s.id)
  await loadSessions()
}

async function onRename(s, ev) {
  menuOpenId.value = null
  ev.stopPropagation()
  const next = window.prompt('重命名会话', s.title)
  if (next == null) return
  const title = next.trim()
  if (!title) return
  await patchSession(s.id, title)
  await loadSessions()
}

async function onShareSession(s, ev) {
  menuOpenId.value = null
  ev.stopPropagation()
  try {
    const result = await shareSession(s.id)
    await copySharePath(result.path)
    alert('分享链接已复制')
  } catch (e) {
    alert(e.message || '生成分享链接失败')
  }
}

async function onAiTitle(s, ev) {
  menuOpenId.value = null
  ev.stopPropagation()
  if (!modelId.value) {
    alert('请先在设置中添加模型')
    return
  }
  if (retitlingId.value != null) return
  retitlingId.value = s.id
  try {
    const result = await retitleSession(s.id, modelId.value)
    const feedback = explainRetitleResult(result)
    if (!feedback.ok) {
      alert(feedback.message)
      return
    }
    await loadSessions()
  } catch (e) {
    alert(e.message || '生成标题失败')
  } finally {
    retitlingId.value = null
  }
}

async function onDelete(s, ev) {
  menuOpenId.value = null
  ev.stopPropagation()
  if (!window.confirm(`删除会话「${s.title}」？`)) return
  await deleteSession(s.id)
  if (currentId.value === s.id) {
    currentId.value = null
  }
  await loadSessions()
}

async function onComposerSend({ content, files, enableThinking }) {
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
  await viewRef.value?.send({ content, files, modelId: modelId.value, enableThinking })
}

function onSent() {
  loadSessions().catch(() => {})
}

onMounted(async () => {
  narrowMq = window.matchMedia(NARROW_QUERY)
  applyNarrow()
  narrowMq.addEventListener('change', applyNarrow)
  window.addEventListener('keydown', onDrawerKey)
  document.addEventListener('pointerdown', onDocPointer)
  try {
    await Promise.all([loadSessions(), loadModels()])
  } catch {
    /* 401 redirects via jsonFetch */
  }
})

onUnmounted(() => {
  if (narrowMq) narrowMq.removeEventListener('change', applyNarrow)
  window.removeEventListener('keydown', onDrawerKey)
  document.removeEventListener('pointerdown', onDocPointer)
  document.body.style.overflow = ''
})

watch([drawerOpen, narrow], ([open, isNarrow]) => {
  document.body.style.overflow = open && isNarrow ? 'hidden' : ''
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
  <div class="shell" :class="{ 'drawer-open': drawerOpen && narrow }">
    <button
      v-show="narrow && drawerOpen"
      type="button"
      class="drawer-backdrop"
      aria-label="关闭会话列表"
      @click="onBackdrop"
    ></button>
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
            :class="{ active: currentId === s.id, pinned: s.pinned }"
            @click="onSelect(s)"
          >
            <div class="session-head">
              <span class="session-title" :title="s.title">{{ s.title }}</span>
              <span v-if="sessionActionsMode(narrow) === 'icons'" class="session-actions icons">
                <button
                  v-if="s.pinned"
                  type="button"
                  class="icon-btn"
                  title="取消置顶"
                  aria-label="取消置顶"
                  @click="onUnpin(s, $event)"
                >
                  <Icon name="unpin" />
                </button>
                <button type="button" class="icon-btn" title="置顶" aria-label="置顶" @click="onPin(s, $event)">
                  <Icon name="pin" />
                </button>
                <button type="button" class="icon-btn" title="重命名" aria-label="重命名" @click="onRename(s, $event)">
                  <Icon name="quill" />
                </button>
                <button
                  type="button"
                  class="icon-btn"
                  title="分享会话"
                  aria-label="分享会话"
                  @click="onShareSession(s, $event)"
                >
                  <Icon name="link" />
                </button>
                <button
                  type="button"
                  class="icon-btn"
                  title="用 AI 生成标题"
                  aria-label="用 AI 生成标题"
                  :disabled="retitlingId != null"
                  @click="onAiTitle(s, $event)"
                >
                  <span v-if="retitlingId === s.id" class="msg-spinner" aria-hidden="true"></span>
                  <Icon v-else name="spark" />
                </button>
                <button type="button" class="icon-btn danger" title="删除" aria-label="删除" @click="onDelete(s, $event)">
                  <Icon name="inkx" />
                </button>
              </span>
              <span v-else class="session-actions menu">
                <button
                  type="button"
                  class="more-session"
                  aria-label="更多"
                  @click.stop="menuOpenId = menuOpenId === s.id ? null : s.id"
                >
                  更多
                </button>
                <ul v-if="menuOpenId === s.id" class="session-menu">
                  <li>
                    <button v-if="s.pinned" type="button" @click="onUnpin(s, $event)">取消置顶</button>
                    <button v-else type="button" @click="onPin(s, $event)">置顶</button>
                  </li>
                  <li>
                    <button type="button" @click="onRename(s, $event)">重命名</button>
                  </li>
                  <li>
                    <button type="button" @click="onShareSession(s, $event)">分享会话</button>
                  </li>
                  <li>
                    <button type="button" :disabled="retitlingId != null" @click="onAiTitle(s, $event)">
                      用 AI 生成标题
                    </button>
                  </li>
                  <li>
                    <button type="button" class="danger" @click="onDelete(s, $event)">删除</button>
                  </li>
                </ul>
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
      <header class="chat-topbar">
        <button type="button" class="icon-btn" aria-label="会话列表" @click="onHamburger">
          <Icon name="menu" />
        </button>
        <span class="topbar-title">{{ currentTitle }}</span>
        <button type="button" class="new-chat" @click="onNewChat">新对话</button>
      </header>
      <RouterView v-slot="{ Component }">
        <component
          :is="Component"
          ref="viewRef"
          :current-id="currentId"
          :model-id="modelId"
          @sent="onSent"
          @compose="onComposerSend"
          @retitled="onSent"
        />
      </RouterView>
    </main>
  </div>
</template>
