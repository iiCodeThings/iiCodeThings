import { describe, expect, it } from 'vitest'
import { tokenizeQuery } from './searchQuery.js'

describe('tokenizeQuery', () => {
  it('splits on whitespace and drops empties', () => {
    expect(tokenizeQuery('韦伯  人类学')).toEqual(['韦伯', '人类学'])
  })
})
