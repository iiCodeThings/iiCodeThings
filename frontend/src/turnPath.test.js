import { describe, expect, it } from 'vitest'
import { turnPath } from './turnPath.js'

describe('turnPath', () => {
  it('builds /r/{sessionId}/{messageId}', () => {
    expect(turnPath(3, 9)).toBe('/r/3/9')
    expect(turnPath('3', '9')).toBe('/r/3/9')
  })
})
