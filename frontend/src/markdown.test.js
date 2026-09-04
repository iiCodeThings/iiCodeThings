/** @vitest-environment happy-dom */
import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown.js'

describe('renderMarkdown', () => {
  it('renders emphasis, lists, and code', () => {
    const html = renderMarkdown('**粗体**\n\n- 甲\n- 乙\n\n`code`')
    expect(html).toContain('<strong>粗体</strong>')
    expect(html).toMatch(/<li>\s*甲\s*<\/li>/)
    expect(html).toContain('<code>code</code>')
    expect(html).not.toContain('**粗体**')
  })

  it('strips script tags', () => {
    const html = renderMarkdown('hi<script>alert(1)</script>')
    expect(html.toLowerCase()).not.toContain('<script')
    expect(html).toContain('hi')
  })

  it('turns single newlines into breaks', () => {
    const html = renderMarkdown('上\n下')
    expect(html).toContain('<br')
  })
})
