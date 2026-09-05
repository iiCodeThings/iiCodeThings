# 可选推理

日期：2026-09-05

推理改为可选。默认关闭：上游收到 `enable_thinking: false`，直接给回答。需要时在输入框勾选「推理」。

## 1. 输入框

- 附件按钮和「发送」之间增加勾选「推理」，默认不勾。
- 本页停留期间保持勾选状态；刷新后回到关。
- 发送时带上当前勾选值，不因发送而重置（除非刷新）。
- 历史助手消息若已有 `reasoning`，展示逻辑不变（直播中展开、历史默认折叠）。

## 2. 发送接口

`POST /api/sessions/{id}/messages` multipart 增加字段 `enable_thinking`：

- 缺省或无法解析 → `false`
- `"true"` / `"1"` / `"on"` → `true`，其余 → `false`

`stream_chat_completion` 的 JSON 增加 `enable_thinking`（与 `model`、`messages`、`stream` 并列）。

关闭推理时：

- 仍把 `enable_thinking: false` 传给上游。
- 若上游仍推送 `reasoning` / `reasoning_content`：不向浏览器发 `reasoning` SSE，不写入 `messages.reasoning`。

打开推理时：行为与现在相同（SSE `reasoning`、入库、前端展示）。

## 3. 重建标题

`chat_completion` 始终带 `enable_thinking: false`。不增加设置项。

## 4. 测试

- 默认 / 未传 `enable_thinking`：发给上游的 payload 含 `enable_thinking is False`。
- 显式打开：payload 为 `True`，mock 的 reasoning 会入库。
- 关闭时 mock 仍返回 reasoning：响应无 reasoning 事件，库中 `reasoning is None`。
- `chat_completion` 请求体含 `enable_thinking is False`。
- 前端：勾选默认 false；`send` 事件带 `enableThinking`。

## 5. 明确不做

- 不按模型单独存默认值，不写 localStorage。
- 不改 Command 键，不改搜索。
- 不保证所有上游都认识 `enable_thinking`；不认识时由上游忽略或报错，本版不兼容多套字段名。
