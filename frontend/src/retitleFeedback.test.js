import { describe, expect, it } from 'vitest'
import { explainRetitleResult } from './retitleFeedback.js'

describe('explainRetitleResult', () => {
  it('reports an empty session as not ok', () => {
    expect(explainRetitleResult({ skipped: true, reason: 'no_messages' })).toEqual({
      ok: false,
      message: '该会话没有消息，无法生成标题',
    })
  })

  it('treats a titled session as success', () => {
    expect(explainRetitleResult({ id: 1, title: '新标题' })).toEqual({ ok: true })
  })
})
