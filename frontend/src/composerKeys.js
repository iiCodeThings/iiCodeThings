export function shouldSendOnKeydown(event) {
  if (event.isComposing || event.keyCode === 229) return false
  if (event.key !== 'Enter') return false
  return Boolean(event.ctrlKey || event.shiftKey)
}
