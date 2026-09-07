<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { searchMessages } from '../api.js'
import Icon from '../components/Icons.vue'
import { renderMarkdown } from '../markdown.js'
import { previewText } from '../searchPreview.js'
import { turnPath } from '../turnPath.js'

const q = ref('')
const hits = ref([])
const expanded = ref(new Set())
const searched = ref(false)
const loading = ref(false)
let timer = null

const active = computed(() => searched.value)

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function isOpen(id) {
  return expanded.value.has(id)
}

function toggle(id) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

async function run(query) {
  const trimmed = query.trim()
  if (!trimmed) {
    hits.value = []
    searched.value = false
    expanded.value = new Set()
    return
  }
  loading.value = true
  try {
    const data = await searchMessages(trimmed)
    hits.value = data.messages || []
    searched.value = true
    expanded.value = new Set()
  } catch {
    hits.value = []
    searched.value = true
  } finally {
    loading.value = false
  }
}

watch(q, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    run(value).catch(() => {})
  }, 280)
})

onMounted(() => {
  run('').catch(() => {})
})
</script>

<template>
  <div class="search-page" :class="{ 'is-active': active }">
    <div class="search-aurora" aria-hidden="true"></div>
    <header class="search-hero">
      <div class="brand search-brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <span class="brand-name">检索</span>
      </div>
      <label class="search-shell">
        <span class="sr-only">搜索对话内容</span>
        <input
          v-model="q"
          class="search-omnibox"
          type="search"
          placeholder="搜索对话内容…"
          autofocus
        />
        <span class="search-orb" aria-hidden="true"></span>
      </label>
      <p v-if="!active" class="search-hint">空格分词，多词同时出现才会命中</p>
    </header>

    <section v-if="active" class="search-panel">
      <p class="search-meta">
        <span v-if="loading">检索中…</span>
        <span v-else>{{ hits.length }} 条结果</span>
      </p>
      <TransitionGroup v-if="hits.length" name="hit" tag="ul" class="hit-list">
        <li v-for="(hit, i) in hits" :key="hit.id" class="hit-card" :style="{ '--i': i }">
          <RouterLink class="hit-link" :to="turnPath(hit.session_id, hit.id)">
            <div class="hit-head">
              <span class="hit-role" :class="hit.role">{{ hit.role === 'user' ? '问' : '答' }}</span>
              <span class="hit-title" :title="hit.session_title || '未命名对话'">{{ hit.session_title || '未命名对话' }}</span>
              <span class="hit-time">{{ formatTime(hit.created_at) }}</span>
            </div>
            <div v-if="isOpen(hit.id)" class="hit-body md" v-html="renderMarkdown(hit.content)"></div>
            <p v-else class="hit-preview">{{ previewText(hit.content).text }}</p>
          </RouterLink>
          <button
            v-if="previewText(hit.content).more || isOpen(hit.id)"
            type="button"
            class="more-btn"
            :class="{ open: isOpen(hit.id) }"
            :aria-label="isOpen(hit.id) ? '收起' : '展开全文'"
            :title="isOpen(hit.id) ? '收起' : '展开全文'"
            @click.stop="toggle(hit.id)"
          >
            <Icon name="more" />
          </button>
        </li>
      </TransitionGroup>
      <p v-else-if="!loading" class="search-empty">没有找到相关内容</p>
    </section>
  </div>
</template>
