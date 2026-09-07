<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchTurn, shareTurn } from '../api.js'
import ShareArticle from '../components/ShareArticle.vue'
import { copySharePath } from '../shareLink.js'

const route = useRoute()
const title = ref('')
const kind = ref('turn')
const messages = ref([])
const userMessageId = ref(null)
const error = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchTurn(route.params.sessionId, route.params.messageId)
    title.value = data.title || '对话'
    kind.value = data.kind || 'turn'
    messages.value = data.messages || []
    userMessageId.value = data.user_message_id ?? null
  } catch (e) {
    error.value = e.message || '这一轮不存在'
    messages.value = []
    userMessageId.value = null
  } finally {
    loading.value = false
  }
}

async function onShare() {
  if (userMessageId.value == null) {
    alert('找不到对应的问题，无法分享')
    return
  }
  try {
    const result = await shareTurn(route.params.sessionId, userMessageId.value)
    await copySharePath(result.path)
    alert('分享链接已复制')
  } catch (e) {
    alert(e.message || '生成分享链接失败')
  }
}

watch(
  () => [route.params.sessionId, route.params.messageId],
  () => {
    load().catch(() => {})
  },
  { immediate: true },
)
</script>

<template>
  <div class="share-page">
    <ShareArticle
      v-if="!loading && !error"
      :title="title"
      :kind="kind"
      :messages="messages"
      footer="只读预览"
    >
      <template #header-extra>
        <button type="button" class="share-make-link" @click="onShare">生成分享链接</button>
      </template>
    </ShareArticle>
    <p v-else-if="loading" class="share-status">载入中…</p>
    <p v-else class="share-status">{{ error }}</p>
  </div>
</template>
