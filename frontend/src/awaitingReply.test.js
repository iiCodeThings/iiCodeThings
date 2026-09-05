import { describe, expect, it } from 'vitest'
import { isAwaitingReply } from './awaitingReply.js'

describe('isAwaitingReply', () => {
  it('is true only while the live assistant has no content or reasoning yet', () => {
    expect(isAwaitingReply({ live: true, content: '', reasoning: '' })).toBe(true)
    expect(isAwaitingReply({ live: true, content: 'hi', reasoning: '' })).toBe(false)
    expect(isAwaitingReply({ live: true, content: '', reasoning: 'think' })).toBe(false)
    expect(isAwaitingReply({ live: false, content: '', reasoning: '' })).toBe(false)
  })
})
