<script setup>
import { ref } from 'vue'
import MessagePane from '../components/MessagePane.vue'

defineProps({
  currentId: { type: [Number, String, null], default: null },
  modelId: { type: [Number, String, null], default: null },
  hitMessageId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['sent'])
const pane = ref(null)

defineExpose({
  send: (opts) => pane.value?.send(opts),
})
</script>

<template>
  <MessagePane
    v-if="currentId"
    ref="pane"
    :session-id="currentId"
    :hit-message-id="hitMessageId"
    @sent="emit('sent')"
  />
  <div v-else class="chat-placeholder">选择或新建对话</div>
</template>
