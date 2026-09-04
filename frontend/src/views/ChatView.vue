<script setup>
import { ref } from 'vue'
import Composer from '../components/Composer.vue'
import MessagePane from '../components/MessagePane.vue'

const props = defineProps({
  currentId: { type: [Number, String, null], default: null },
  modelId: { type: [Number, String, null], default: null },
  hitMessageId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['sent', 'compose'])
const pane = ref(null)

defineExpose({
  send: (opts) => pane.value?.send(opts),
})
</script>

<template>
  <div class="chat-col">
    <MessagePane
      v-if="currentId"
      :key="currentId"
      ref="pane"
      :session-id="currentId"
      :hit-message-id="hitMessageId"
      @sent="emit('sent')"
    />
    <div v-else class="chat-placeholder">
      <span class="placeholder-mark" aria-hidden="true"></span>
      <p>选择左侧会话，或点「新对话」开始</p>
    </div>
    <Composer :model-id="props.modelId" :session-id="props.currentId" @send="emit('compose', $event)" />
  </div>
</template>
