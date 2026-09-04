import { parseSseChunk } from './sse.js'

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

export async function listMessages(sessionId, { beforeId, limit } = {}) {
  const params = new URLSearchParams()
  if (beforeId != null) params.set('before_id', String(beforeId))
  if (limit != null) params.set('limit', String(limit))
  const qs = params.toString()
  const res = await jsonFetch(`/api/sessions/${sessionId}/messages${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error('加载消息失败')
  return res.json()
}

export async function searchSessions(q) {
  const res = await jsonFetch(`/api/search?q=${encodeURIComponent(q ?? '')}`)
  if (!res.ok) throw new Error('搜索失败')
  return res.json()
}

function errorDetail(data, fallback) {
  if (typeof data?.detail === 'string') return data.detail
  return fallback
}

export async function sendMessage({
  sessionId,
  content,
  modelId,
  files,
  onDelta,
  onReasoning,
  onTruncated,
  onDone,
  onError,
}) {
  const fd = new FormData()
  fd.append('content', content ?? '')
  fd.append('model_id', String(modelId))
  if (files) {
    for (const file of files) {
      fd.append('files', file)
    }
  }
  const res = await fetch(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    credentials: 'include',
    body: fd,
  })
  if (res.status === 401 && !window.location.pathname.startsWith('/login')) {
    window.location = '/login'
    throw new Error('unauthorized')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    onError?.(errorDetail(data, '发送失败'), { http: true })
    return
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  function dispatch(events) {
    for (const ev of events) {
      if (ev.event === 'delta') onDelta?.(ev.data)
      else if (ev.event === 'reasoning') onReasoning?.(ev.data)
      else if (ev.event === 'truncated') onTruncated?.(ev.data)
      else if (ev.event === 'done') onDone?.(ev.data)
      else if (ev.event === 'error') onError?.(ev.data?.text || '生成失败', { http: false })
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parsed = parseSseChunk(buffer)
    buffer = parsed.rest
    dispatch(parsed.events)
  }
  buffer += decoder.decode()
  if (buffer.trim()) {
    const parsed = parseSseChunk(buffer.endsWith('\n\n') ? buffer : `${buffer}\n\n`)
    dispatch(parsed.events)
  }
}

export const acceptAttr = '.jpg,.jpeg,.png,.webp,.txt,.md,.doc,.docx'
