import { describe, expect, it } from 'vitest'
import { acceptAttr } from './api.js'

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
