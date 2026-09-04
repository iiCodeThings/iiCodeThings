export function parseSseChunk(buffer) {
  const parts = buffer.split('\n\n')
  const rest = parts.pop()
  const events = []
  for (const block of parts) {
    let event = 'message'
    let data = ''
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      if (line.startsWith('data:')) data += line.slice(5).trim()
    }
    if (data) events.push({ event, data: JSON.parse(data) })
  }
  return { events, rest }
}
