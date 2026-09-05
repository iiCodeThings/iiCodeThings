export function explainRetitleResult(data) {
  if (data?.skipped) {
    return { ok: false, message: '该会话没有消息，无法生成标题' }
  }
  return { ok: true }
}
