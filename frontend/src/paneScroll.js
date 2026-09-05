export const BOTTOM_THRESHOLD = 80

export function isNearBottom(
  { scrollTop, scrollHeight, clientHeight },
  threshold = BOTTOM_THRESHOLD,
) {
  return scrollHeight - scrollTop - clientHeight <= threshold
}
