export function tokenizeQuery(q) {
  return q.split(/\s+/).filter(Boolean)
}
