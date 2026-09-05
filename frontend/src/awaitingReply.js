export function isAwaitingReply({ live, content, reasoning }) {
  return Boolean(live && !content && !reasoning)
}
