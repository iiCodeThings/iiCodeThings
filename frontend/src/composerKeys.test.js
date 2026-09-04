import { describe, expect, it } from 'vitest'
import { shouldSendOnKeydown } from './composerKeys.js'

function ev(partial) {
  return {
    key: 'Enter',
    ctrlKey: false,
    shiftKey: false,
    metaKey: false,
    isComposing: false,
    keyCode: 13,
    ...partial,
  }
}

describe('shouldSendOnKeydown', () => {
  it('does not send on plain Enter', () => {
    expect(shouldSendOnKeydown(ev())).toBe(false)
  })
  it('sends on Ctrl+Enter', () => {
    expect(shouldSendOnKeydown(ev({ ctrlKey: true }))).toBe(true)
  })
  it('sends on Shift+Enter', () => {
    expect(shouldSendOnKeydown(ev({ shiftKey: true }))).toBe(true)
  })
  it('does not send on Command+Enter', () => {
    expect(shouldSendOnKeydown(ev({ metaKey: true }))).toBe(false)
  })
  it('does not send while composing', () => {
    expect(shouldSendOnKeydown(ev({ ctrlKey: true, isComposing: true }))).toBe(false)
    expect(shouldSendOnKeydown(ev({ ctrlKey: true, keyCode: 229 }))).toBe(false)
  })
})
