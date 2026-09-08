import { describe, expect, it } from 'vitest'
import {
  SLASH_COMMANDS,
  completeSlashCommand,
  matchSlashCommands,
  parseSearchCommand,
  slashCommandDraft,
} from './slashCommands.js'

describe('SLASH_COMMANDS', () => {
  it('lists new-session then search', () => {
    expect(SLASH_COMMANDS.map((c) => c.command)).toEqual(['/new-session', '/search'])
    expect(SLASH_COMMANDS[0].hint).toBe('新建会话')
    expect(SLASH_COMMANDS[1].hint).toBe('打开搜索')
  })
})

describe('slashCommandDraft', () => {
  it('returns the trimStarted slash token when there is no space', () => {
    expect(slashCommandDraft('/')).toBe('/')
    expect(slashCommandDraft('  /n')).toBe('/n')
    expect(slashCommandDraft('/new-session')).toBe('/new-session')
    expect(slashCommandDraft('/s')).toBe('/s')
  })

  it('returns null when not a command draft', () => {
    expect(slashCommandDraft('')).toBe(null)
    expect(slashCommandDraft('hello')).toBe(null)
    expect(slashCommandDraft('/new-session ')).toBe(null)
    expect(slashCommandDraft('/search ')).toBe(null)
    expect(slashCommandDraft('/new-session 韦伯')).toBe(null)
  })
})

describe('matchSlashCommands', () => {
  it('filters by case-sensitive prefix', () => {
    expect(matchSlashCommands('/').map((c) => c.command)).toEqual(['/new-session', '/search'])
    expect(matchSlashCommands('/n').map((c) => c.command)).toEqual(['/new-session'])
    expect(matchSlashCommands('/s').map((c) => c.command)).toEqual(['/search'])
    expect(matchSlashCommands('/N')).toEqual([])
    expect(matchSlashCommands('/foo')).toEqual([])
  })
})

describe('completeSlashCommand', () => {
  it('appends a single trailing space', () => {
    expect(completeSlashCommand('/new-session')).toBe('/new-session ')
    expect(completeSlashCommand('/search')).toBe('/search ')
  })
})

describe('parseSearchCommand', () => {
  it('returns null when not a search command', () => {
    expect(parseSearchCommand('')).toBe(null)
    expect(parseSearchCommand('hello')).toBe(null)
    expect(parseSearchCommand('/SEARCH')).toBe(null)
    expect(parseSearchCommand('/new-session')).toBe(null)
  })

  it('returns a truthy value for /search prefix', () => {
    expect(parseSearchCommand('/search')).toEqual({ ok: true })
    expect(parseSearchCommand('  /search  ')).toEqual({ ok: true })
    expect(parseSearchCommand('/search foo')).toEqual({ ok: true })
    expect(parseSearchCommand('/searchfoo')).toEqual({ ok: true })
  })
})
