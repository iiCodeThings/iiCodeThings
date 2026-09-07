<script setup>
import { renderMarkdown } from '../markdown.js'

defineProps({
  title: { type: String, default: '' },
  kind: { type: String, default: 'turn' },
  messages: { type: Array, default: () => [] },
  footer: { type: String, default: '只读分享' },
})
</script>

<template>
  <article class="share-article">
    <header class="share-header">
      <div class="share-header-row">
        <div>
          <p class="share-kicker">{{ kind === 'turn' ? '一问一答' : '对话全文' }}</p>
          <h1>{{ title }}</h1>
        </div>
        <slot name="header-extra"></slot>
      </div>
    </header>
    <section v-for="(m, i) in messages" :key="i" class="share-block" :class="m.role">
      <p class="share-label">{{ m.role === 'user' ? '问' : '答' }}</p>
      <div v-if="m.content" class="share-body md" v-html="renderMarkdown(m.content)"></div>
      <ul v-if="m.attachments && m.attachments.length" class="share-files">
        <li v-for="(a, j) in m.attachments" :key="j">{{ a.original_filename }}</li>
      </ul>
    </section>
    <footer class="share-foot">{{ footer }}</footer>
  </article>
</template>
