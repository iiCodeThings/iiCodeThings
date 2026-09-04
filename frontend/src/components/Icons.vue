<script setup>
defineProps({
  name: { type: String, required: true },
})
</script>

<template>
  <!-- 羽毛笔：重命名 -->
  <svg
    v-if="name === 'quill'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M18.6 3.2c.2 2.4-1.1 4.8-3.6 7.6-2.4 2.7-5.4 5.1-8.8 7.4"
      stroke="currentColor"
      stroke-width="1.45"
      stroke-linecap="round"
    />
    <path
      d="M16.4 4.6c.7 1.5.8 3.2.1 4.8M12.8 8.4c-1.6 1.8-3.5 3.4-5.6 5"
      stroke="currentColor"
      stroke-width="1.15"
      stroke-linecap="round"
      opacity="0.7"
    />
    <path
      d="M5.2 19.4c1.4-1.6 2.9-2.8 4.6-3.8"
      stroke="currentColor"
      stroke-width="1.35"
      stroke-linecap="round"
    />
    <path
      d="M4.2 20.8c.55.35 1.2.55 1.85.5.4-.55.55-1.25.4-1.95"
      stroke="currentColor"
      stroke-width="1.35"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>

  <!-- 水墨叉：删除 -->
  <svg
    v-else-if="name === 'inkx'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M6.2 6.4c2.8 2.4 5.6 5.3 11.4 11.8"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
    />
    <path
      d="M17.8 6.8c-2.6 2.6-5.8 5.6-11.6 10.8"
      stroke="currentColor"
      stroke-width="1.45"
      stroke-linecap="round"
    />
    <circle cx="7.2" cy="17.6" r="1.15" fill="currentColor" opacity="0.55" />
    <circle cx="16.6" cy="7.4" r="0.7" fill="currentColor" opacity="0.4" />
  </svg>

  <!-- 回形针：附件 -->
  <svg
    v-else-if="name === 'clip'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M8.2 12.4l6.4-6.4a3.2 3.2 0 1 1 4.5 4.5l-8.2 8.2a4.4 4.4 0 0 1-6.2-6.2l7.6-7.6"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>

  <!-- 展开 / 收起 -->
  <svg
    v-else-if="name === 'more'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M5 9.2c2.4 1.4 4.6 4.6 7 7.6 2.4-3 4.7-6.2 7.1-7.6"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>

  <!-- 图钉：置顶 -->
  <svg
    v-else-if="name === 'pin'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <circle
      cx="12"
      cy="7.2"
      r="3.1"
      stroke="currentColor"
      stroke-width="1.45"
    />
    <path
      d="M12 10.4v9.2"
      stroke="currentColor"
      stroke-width="1.45"
      stroke-linecap="round"
    />
    <path
      d="M9.6 12.2h4.8"
      stroke="currentColor"
      stroke-width="1.25"
      stroke-linecap="round"
      opacity="0.75"
    />
  </svg>

  <!-- 图钉斜线：取消置顶 -->
  <svg
    v-else-if="name === 'unpin'"
    class="icon"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <circle
      cx="12"
      cy="7.2"
      r="3.1"
      stroke="currentColor"
      stroke-width="1.45"
    />
    <path
      d="M12 10.4v9.2"
      stroke="currentColor"
      stroke-width="1.45"
      stroke-linecap="round"
    />
    <path
      d="M9.6 12.2h4.8"
      stroke="currentColor"
      stroke-width="1.25"
      stroke-linecap="round"
      opacity="0.75"
    />
    <path
      d="M6.2 5.8l11.6 12.4"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
    />
  </svg>
</template>
