export const PREVIEW_LEN = 180

export function previewText(content) {
  const text = String(content || "")
    .replace(/\s+/g, " ")
    .trim()
  if (text.length <= PREVIEW_LEN) {
    return { text, more: false }
  }
  return { text: text.slice(0, PREVIEW_LEN).trimEnd(), more: true }
}
