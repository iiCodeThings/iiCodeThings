import { describe, expect, it } from 'vitest'
import { parseNewSessionCommand } from './newSessionCommand.js'

describe('parseNewSessionCommand', () => {
  it('returns null when not a command', () => {
    expect(parseNewSessionCommand('')).toBe(null)
    expect(parseNewSessionCommand('hello')).toBe(null)
    expect(parseNewSessionCommand('/NEW-SESSION')).toBe(null)
    expect(parseNewSessionCommand('x /new-session')).toBe(null)
  })

  it('treats prefix match as a command', () => {
    expect(parseNewSessionCommand('/new-session')).toEqual({ title: null })
    expect(parseNewSessionCommand('  /new-session  ')).toEqual({ title: null })
    expect(parseNewSessionCommand('/new-session   ')).toEqual({ title: null })
    expect(parseNewSessionCommand('/new-session 韦伯笔记')).toEqual({ title: '韦伯笔记' })
    expect(parseNewSessionCommand('/new-sessionfoo')).toEqual({ title: 'foo' })
  })
})
