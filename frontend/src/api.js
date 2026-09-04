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
