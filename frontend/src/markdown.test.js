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

  it('emphasizes text wrapped in CJK quotation marks', () => {
    const html = renderMarkdown(
      '[这种持续的压力会耗尽心理资源，导致**“情绪耗竭”**，表现出的就是对什么都提不起劲]',
    )
    expect(html).toContain('<strong>')
    expect(html).toContain('情绪耗竭')
    expect(html).not.toContain('**')
  })

  it('emphasizes CJK-quoted phrases without surrounding brackets', () => {
    const html = renderMarkdown('导致**“情绪耗竭”**，表现')
    expect(html).toContain('<strong>')
    expect(html).toContain('情绪耗竭')
    expect(html).not.toContain('**')
  })

  it('leaves emphasis markers intact inside code', () => {
    const html = renderMarkdown('看 `导致**“情绪耗竭”**`')
    expect(html).toContain('<code>')
    expect(html).toContain('**')
    expect(html).not.toMatch(/<code>[^<]*<strong>/)
  })
})
