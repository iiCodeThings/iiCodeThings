<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api.js'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
    router.push('/')
  } catch {
    error.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <h1>登录</h1>
    <form @submit.prevent="onSubmit">
      <label>
        用户名
        <input v-model="username" name="username" autocomplete="username" required />
      </label>
      <label>
        密码
        <input
          v-model="password"
          name="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="loading">登录</button>
    </form>
  </div>
</template>
