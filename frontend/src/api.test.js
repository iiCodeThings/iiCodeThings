import { afterEach, describe, expect, it } from 'vitest'
import { acceptAttr, fetchTurn } from './api.js'

describe('acceptAttr', () => {
  it('includes .png and .md', () => {
    expect(acceptAttr).toContain('.png')
    expect(acceptAttr).toContain('.md')
    expect(acceptAttr).toContain('.pdf')
    expect(acceptAttr).toContain('.xlsx')
    expect(acceptAttr).toContain('.csv')
    expect(acceptAttr).toContain('.json')
  })
})

describe('fetchTurn', () => {
  const orig = globalThis.fetch
  afterEach(() => {
    globalThis.fetch = orig
  })

  it('GETs /api/sessions/:id/turns/:messageId', async () => {
    globalThis.fetch = async (url, opts) => {
      expect(url).toBe('/api/sessions/3/turns/9')
      expect(opts.credentials).toBe('include')
      return {
        status: 200,
        ok: true,
        json: async () => ({ kind: 'turn', user_message_id: 8, messages: [] }),
      }
    }
    const data = await fetchTurn(3, 9)
    expect(data.user_message_id).toBe(8)
  })

  it('throws 这一轮不存在 on 404', async () => {
    globalThis.fetch = async () => ({ status: 404, ok: false, json: async () => ({}) })
    await expect(fetchTurn(1, 2)).rejects.toThrow('这一轮不存在')
  })
})
