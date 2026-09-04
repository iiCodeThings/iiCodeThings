import { describe, expect, it } from 'vitest'
import { PREVIEW_LEN, previewText } from './searchPreview.js'

describe('previewText', () => {
  it('keeps short text whole', () => {
    expect(previewText('韦伯')).toEqual({ text: '韦伯', more: false })
  })

  it('marks long text as needing more', () => {
    const long = '甲'.repeat(PREVIEW_LEN + 8)
    const out = previewText(long)
    expect(out.more).toBe(true)
    expect(out.text.length).toBeLessThan(long.length)
  })
})
