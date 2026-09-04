<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  changePassword,
  createModel,
  deleteModel,
  listModels,
  updateModel,
} from '../api.js'

const router = useRouter()
const models = ref([])
const error = ref('')
const passwordMsg = ref('')

const form = reactive({
  id: null,
  name: '',
  base_url: '',
  api_key: '',
  model: '',
  supports_vision: false,
  sort_order: 0,
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
})

async function loadModels() {
  models.value = await listModels()
}

function resetForm() {
  form.id = null
  form.name = ''
  form.base_url = ''
  form.api_key = ''
  form.model = ''
  form.supports_vision = false
  form.sort_order = 0
}

function editModel(m) {
  form.id = m.id
  form.name = m.name
  form.base_url = m.base_url
  form.api_key = ''
  form.model = m.model
  form.supports_vision = m.supports_vision
  form.sort_order = m.sort_order
}

async function onSaveModel() {
  error.value = ''
  const body = {
    name: form.name,
    base_url: form.base_url,
    api_key: form.api_key || null,
    model: form.model,
    supports_vision: form.supports_vision,
    sort_order: Number(form.sort_order) || 0,
  }
  try {
    if (form.id) {
      await updateModel(form.id, body)
    } else {
      await createModel(body)
    }
    resetForm()
    await loadModels()
  } catch (e) {
    error.value = e.message || '保存失败'
  }
}

async function onDeleteModel(id) {
  error.value = ''
  try {
    await deleteModel(id)
    if (form.id === id) resetForm()
    await loadModels()
  } catch (e) {
    error.value = e.message || '删除失败'
  }
}

async function onChangePassword() {
  passwordMsg.value = ''
  error.value = ''
  try {
    await changePassword(passwordForm.old_password, passwordForm.new_password)
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordMsg.value = '密码已修改，请重新登录'
    router.push('/login')
  } catch (e) {
    error.value = e.message || '改密失败'
  }
}

onMounted(async () => {
  try {
    await loadModels()
  } catch {
    /* 401 redirects */
  }
})
</script>

<template>
  <div class="settings">
    <h1>设置</h1>

    <section>
      <h2>模型</h2>
      <ul class="model-list" v-if="models.length">
        <li v-for="m in models" :key="m.id">
          <span>{{ m.name }} ({{ m.model }})</span>
          <button type="button" @click="editModel(m)">编辑</button>
          <button type="button" @click="onDeleteModel(m.id)">删除</button>
        </li>
      </ul>
      <form class="model-form" @submit.prevent="onSaveModel">
        <label>
          名称
          <input v-model="form.name" name="name" required />
        </label>
        <label>
          接口地址
          <input v-model="form.base_url" name="base_url" required />
        </label>
        <label>
          API Key
          <input v-model="form.api_key" name="api_key" type="password" :required="!form.id" />
        </label>
        <label>
          模型 ID
          <input v-model="form.model" name="model" required />
        </label>
        <label class="checkbox">
          <input v-model="form.supports_vision" name="supports_vision" type="checkbox" />
          支持图片
        </label>
        <label>
          排序
          <input v-model.number="form.sort_order" name="sort_order" type="number" />
        </label>
        <button type="submit">{{ form.id ? '更新模型' : '添加模型' }}</button>
        <button v-if="form.id" type="button" @click="resetForm">取消</button>
      </form>
    </section>

    <section>
      <h2>修改密码</h2>
      <form class="password-form" @submit.prevent="onChangePassword">
        <label>
          当前密码
          <input
            v-model="passwordForm.old_password"
            name="old_password"
            type="password"
            required
          />
        </label>
        <label>
          新密码
          <input
            v-model="passwordForm.new_password"
            name="new_password"
            type="password"
            minlength="6"
            required
          />
        </label>
        <button type="submit">修改密码</button>
      </form>
      <p v-if="passwordMsg">{{ passwordMsg }}</p>
    </section>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>
