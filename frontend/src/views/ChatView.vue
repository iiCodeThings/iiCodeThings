<script setup>
defineProps({
  currentId: { type: [Number, String, null], default: null },
  modelId: { type: [Number, String, null], default: null },
})
</script>

<template>
  <div class="chat-placeholder">选择或新建对话</div>
</template>
