<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchShare } from '../api.js'
import { renderMarkdown } from '../markdown.js'

const route = useRoute()
const title = ref('')
const kind = ref('session')
const messages = ref([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await fetchShare(route.params.token)
    title.value = data.title || '对话'
    kind.value = data.kind || 'session'
    messages.value = data.messages || []
  } catch (e) {
    error.value = e.message || '无法打开分享'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="share-page">
    <article v-if="!loading && !error" class="share-article">
      <header class="share-header">
        <p class="share-kicker">{{ kind === 'turn' ? '一问一答' : '对话全文' }}</p>
        <h1>{{ title }}</h1>
      </header>
      <section v-for="(m, i) in messages" :key="i" class="share-block" :class="m.role">
        <p class="share-label">{{ m.role === 'user' ? '问' : '答' }}</p>
        <div v-if="m.content" class="share-body md" v-html="renderMarkdown(m.content)"></div>
        <ul v-if="m.attachments && m.attachments.length" class="share-files">
          <li v-for="(a, j) in m.attachments" :key="j">{{ a.original_filename }}</li>
        </ul>
      </section>
      <footer class="share-foot">只读分享</footer>
    </article>
    <p v-else-if="loading" class="share-status">载入中…</p>
    <p v-else class="share-status">{{ error }}</p>
  </div>
</template>
