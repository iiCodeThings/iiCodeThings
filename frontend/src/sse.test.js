import { describe, expect, it } from 'vitest'
import { parseSseChunk } from './sse.js'

describe('parseSseChunk', () => {
  it('parses a delta event from a complete chunk', () => {
    const { events, rest } = parseSseChunk('event: delta\ndata: {"text":"hi"}\n\n')
    expect(events).toEqual([{ event: 'delta', data: { text: 'hi' } }])
    expect(rest).toBe('')
  })

  it('parses a warning event', () => {
    const { events } = parseSseChunk(
      'event: warning\ndata: {"text":"文档未能抽出文字，已保存原文件"}\n\n',
    )
    expect(events).toEqual([
      { event: 'warning', data: { text: '文档未能抽出文字，已保存原文件' } },
    ])
  })
})
