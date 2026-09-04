export async function jsonFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  if (res.status === 401 && !window.location.pathname.startsWith('/login')) {
    window.location = '/login'
    throw new Error('unauthorized')
  }
  return res
}

export async function login(username, password) {
  const res = await jsonFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    throw new Error('用户名或密码错误')
  }
  return res.json()
}

export async function logout() {
  const res = await jsonFetch('/api/auth/logout', { method: 'POST' })
  if (!res.ok) {
    throw new Error('logout failed')
  }
  return res.json()
}

export async function changePassword(old_password, new_password) {
  const res = await jsonFetch('/api/auth/password', {
    method: 'POST',
    body: JSON.stringify({ old_password, new_password }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || '改密失败')
  }
  return res.json()
}

export async function listSessions() {
  const res = await jsonFetch('/api/sessions')
  if (!res.ok) throw new Error('加载会话失败')
  return res.json()
}

export async function createSession() {
  const res = await jsonFetch('/api/sessions', { method: 'POST' })
  if (!res.ok) throw new Error('创建会话失败')
  return res.json()
}

export async function patchSession(id, title) {
  const res = await jsonFetch(`/api/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error('更新会话失败')
  return res.json()
}

export async function deleteSession(id) {
  const res = await jsonFetch(`/api/sessions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除会话失败')
  return res.json()
}

export async function listModels() {
  const res = await jsonFetch('/api/models')
  if (!res.ok) throw new Error('加载模型失败')
  return res.json()
}

export async function createModel(body) {
  const res = await jsonFetch('/api/models', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || '创建模型失败')
  }
  return res.json()
}

export async function updateModel(id, body) {
  const res = await jsonFetch(`/api/models/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || '更新模型失败')
  }
  return res.json()
}

export async function deleteModel(id) {
  const res = await jsonFetch(`/api/models/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除模型失败')
  return res.json()
}

export const acceptAttr = '.jpg,.jpeg,.png,.webp,.txt,.md,.doc,.docx'
