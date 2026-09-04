# 重建会话标题

日期：2026-09-04

设置页一键用大模型为**全部未删除 session** 重新生成 `title`。导入的历史会话、手动改过的标题都会被覆盖。

## 1. 目标

- 在设置中选择一个已保存的模型，点一个按钮。
- 对每个有消息的 live session：把该 session 的对话内容交给该模型，生成言简意赅的标题并写回 `sessions.title`。
- 没有消息的 session 跳过，不调模型。
- 某个 session 失败则跳过，继续后面的；结束后给出成功 / 跳过 / 失败数量。

## 2. 明确不做

- 不重建已软删除的 session。
- 不把历史 `reasoning` 或图片附件送给模型。
- 不做后台任务队列、不做一次请求改完全部 session 的 bulk 接口、不用 SSE 推整批进度。
- 不按标题筛选（例如只改「新对话」）；范围内全部覆盖。
- 不改消息内容，不改 `updated_at`（避免左栏被刷成全部刚刚更新）。

## 3. 设置页

在「修改密码」旁增加一节 **重建会话标题**：

- 模型下拉：选项与设置页已有模型列表相同。无模型时按钮禁用。
- 按钮文案：`重建全部标题`。
- 点击后先 `confirm`：将用所选模型为所有未删除会话重新生成标题；已有标题（含手动修改）会被覆盖；没有消息的会话会跳过。
- 确认后禁用按钮，显示 `已完成 x/y，失败 z`。
- 全部结束后提示：`完成：成功 n，跳过 m（无消息），失败 k`。
- 每成功改一个，左栏 session 列表立刻刷新标题。
- 离开设置页则停止后续请求；已经写库的标题保留。

## 4. 前端流程

1. `GET /api/sessions` 得到 live session 列表（现有接口）。
2. 按列表顺序，对每个 `id` 调用 `POST /api/sessions/{id}/retitle`，body `{"model_id": <所选模型 id>}`。
3. 串行，一次只跑一个，避免打满上游。
4. 响应分类：
   - `200` 且 `skipped: true` → 跳过 +1
   - `200` 且有 `title` → 成功 +1，刷新左栏列表
   - 其它 HTTP 错误 → 失败 +1，继续下一个

## 5. 接口

`POST /api/sessions/{id}/retitle`

- 需登录。
- Body：`{"model_id": int}`。模型不存在或未传 → `400`，文案「请先在设置中添加模型」。
- Session 不存在或已软删除 → `404`，文案「会话不存在」。
- 该 session 没有任何消息 → `200` `{"skipped": true, "reason": "no_messages"}`，不调模型、不改行。
- 成功 → `200`，形状与现有 session 输出一致：`id`、`title`、`created_at`、`updated_at`（`updated_at` 仍为原值）。
- 上游失败 → `502`，detail 为简短错误；该 session 的 `title` 保持不变。

写入时只更新 `title`（截断到 128 字符），显式保持原来的 `updated_at`。

## 6. 送给模型的内容

新增非流式 `chat_completion`（OpenAI 兼容 `POST /chat/completions`，`stream: false`），与现有流式调用共用 `base_url` / `api_key` / `model`。

消息两条：

1. **system**：根据对话生成会话标题。言简意赅；与对话同一语言；不要引号、句号、不要「标题：」之类前缀；不要解释。
2. **user**：该 session 全部消息按时间正序转写。每条一行：`用户：` / `助手：` + `content`。用户消息若有文档附件，把 `extracted_text` 附在该条正文后。不含 `reasoning`，不含图片。

若上游返回上下文超长（沿用现有 `is_context_length_error`）：从转写里丢掉最早一轮（一对用户+助手，逻辑与 `drop_oldest_turn` 相同）再请求，直到成功或只剩一轮仍失败。只剩一轮仍失败则该 session 记为失败。

模型返回的文本：去掉首尾空白、包裹引号、换行压成空格，再截到 128 字符。若清理后为空，视为该 session 失败，不写库。

## 7. 测试

后端：

- 无消息 → `skipped`，title 不变。
- 有消息且 mock 上游返回标题 → 写入清理后的 title，`updated_at` 不变。
- 不存在的 `model_id` → 400。
- 软删除 session → 404。
- mock 上游 5xx → 502，title 不变。
- 发给上游的 payload **不含** reasoning、**不含** image_url。
- 上下文超长时会丢掉较早轮次后重试。

前端不强制加组件测试；设置页按现有风格接线即可。
