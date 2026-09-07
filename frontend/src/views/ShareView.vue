<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchShare } from '../api.js'
import ShareArticle from '../components/ShareArticle.vue'

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
    <ShareArticle
      v-if="!loading && !error"
      :title="title"
      :kind="kind"
      :messages="messages"
      footer="只读分享"
    />
    <p v-else-if="loading" class="share-status">载入中…</p>
    <p v-else class="share-status">{{ error }}</p>
  </div>
</template>
