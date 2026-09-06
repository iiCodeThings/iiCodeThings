import { absoluteShareUrl } from './api.js'

export async function copySharePath(path) {
  const url = absoluteShareUrl(path)
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    window.prompt('复制分享链接', url)
  }
  return url
}
