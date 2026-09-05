import { describe, expect, it } from 'vitest'
import { isNearBottom } from './paneScroll.js'

describe('isNearBottom', () => {
  it('is true when flush with the bottom', () => {
    expect(isNearBottom({ scrollTop: 400, scrollHeight: 500, clientHeight: 100 })).toBe(true)
  })

  it('is true within the default threshold', () => {
    expect(isNearBottom({ scrollTop: 320, scrollHeight: 500, clientHeight: 100 })).toBe(true)
  })

  it('is false after scrolling up past the threshold', () => {
    expect(isNearBottom({ scrollTop: 200, scrollHeight: 500, clientHeight: 100 })).toBe(false)
  })

  it('is false at the top of a long thread', () => {
    expect(isNearBottom({ scrollTop: 0, scrollHeight: 2000, clientHeight: 400 })).toBe(false)
  })
})
