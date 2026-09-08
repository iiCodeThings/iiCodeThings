export const NARROW_QUERY = '(max-width: 719.98px)'

export function isNarrowViewport(widthPx) {
  return Number(widthPx) < 720
}

export function sessionActionsMode(_narrow) {
  return 'menu'
}

export function nextDrawerOpen({ open, narrow, action }) {
  if (!narrow) return false
  if (action === 'toggle') return !open
  if (action === 'open') return true
  if (
    action === 'close' ||
    action === 'select' ||
    action === 'escape' ||
    action === 'backdrop' ||
    action === 'widen'
  ) {
    return false
  }
  return open
}
