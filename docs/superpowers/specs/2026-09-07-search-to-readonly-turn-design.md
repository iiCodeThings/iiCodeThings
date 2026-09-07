# 搜索结果打开一问一答（可选公开分享）

日期：2026-09-07

搜索命中与公开只读分享 `/s/:token` 之间没有跳转。点搜索结果先打开**需登录**的这一问一答；是否生成无需鉴权的分享链接，由用户在该页上另点一次决定。

## 1. 目标

- `/search` 点一条命中（不是展开）→ `/r/{sessionId}/{messageId}`，只展示这一问一答。
- 打开该页**不**写入 `shares` 表、**不**生成 token。
- 页上「生成分享链接」才调用现有 `POST /api/sessions/{id}/share/turn`，复制 `/s/{token}` 绝对 URL。用户不跳走。
- `messageId` 可以是这一轮的问或答。

## 2. 明确不做

- 不改 `GET /api/search`、`GET /api/search/messages` 的返回字段（不预发 token，不补 `user_message_id`）。
- 不把搜索结果接回聊天页，不接线里闲置的 `hitMessageId`。
- 打开 `/r/...` 或搜索本身都不创建分享。
- 不在只读页展示整段会话。
- 生成链接后不自动打开 `/s/:token`。
- 不改 `POST .../share`、`POST .../share/turn` 的入参与语义。

## 3. 路由与页面

| 路径 | 鉴权 | 作用 |
|------|------|------|
| `/search` | 登录 | 搜索。卡片链到 `/r/{session_id}/{id}` |
| `/r/:sessionId/:messageId` | 登录 | 这一问一答的只读预览；可生成公开链接 |
| `/s/:token` | 无 | 现有公开只读分享，不变 |

`/r/...` 与 `/search`、`/s/:token` 一样是独立页，不进 `AppShell`。未登录请求该页接口 → 401，前端现有逻辑去 `/login`。

## 4. 搜索点击

- 命中卡片（除展开按钮外）是指向 `/r/{hit.session_id}/{hit.id}` 的链接。
- 「展开 / 收起」按钮 `stopPropagation`（或放在链接外），只切换预览，不导航。
- 搜索接口与 debounce 行为不变。

## 5. 鉴权只读接口

`GET /api/sessions/{session_id}/turns/{message_id}`，需登录。

从 `message_id` 定位这一轮：

1. 会话必须存在且未删除；消息必须属于该 `session_id`。否则 404「会话不存在」或「这一轮不存在」。
2. 消息 `role === user`：它就是问。
3. 消息 `role === assistant`：同会话中 `id` 小于它的、最近一条 `role === user` 为问。找不到则 404「这一轮不存在」。
4. 答 = 同会话中 `id` 大于问、最近一条 `role === assistant`（可以没有）。

响应与公开分享的消息形状相同（无 `reasoning`），并带上分享要用的问 id：

```json
{
  "title": "会话标题",
  "kind": "turn",
  "user_message_id": 12,
  "messages": [
    { "role": "user", "content": "...", "model_name": "...", "attachments": [{"kind": "...", "original_filename": "..."}] },
    { "role": "assistant", "content": "...", "model_name": "...", "attachments": [] }
  ]
}
```

没有答时 `messages` 只有问。未登录 401。

定位这一轮的逻辑抽成共用函数：公开 `GET /api/shares/{token}` 在 `kind === turn` 时也走它，避免两套规则。

## 6. 前端组件

- 从 `ShareView` 抽出文章排版组件（标题、问/答块、附件列表）。两边共用。
- `ShareView`：仍按 token 拉公开内容；页脚「只读分享」；无生成按钮。
- 新页 `OwnerTurnView`：按路由参数调第 5 节接口；页脚「只读预览」；标题旁「生成分享链接」。
- `api.js` 增加 `fetchTurn(sessionId, messageId)`，走 `jsonFetch`（401 与现有一致）。

生成分享：

- 使用响应里的 `user_message_id` 调现有 `shareTurn`。
- 成功则 `copySharePath(result.path)`，提示「分享链接已复制」。
- 同一轮再点仍是同一个 token。
- `user_message_id` 缺失时提示「找不到对应的问题，无法分享」（与聊天里一致）。

## 7. 错误

| 情况 | 行为 |
|------|------|
| 未登录打 `GET .../turns/...` | 401 → `/login` |
| 会话已删、消息不在该会话、答找不到对应的问 | 404，只读页显示「这一轮不存在」 |
| 生成分享失败 | `alert` 接口返回的 `detail` 或「生成分享链接失败」 |

## 8. 测试

后端：

- 用问的 id 与答的 id 打同一 `GET .../turns/...`，得到同一对消息和同一个 `user_message_id`。
- 仅有问、尚无答：`messages` 长度为 1。
- 未登录 401；已删会话 / 消息属于别的会话 / 未知 id：404。
- 打开 turn 接口之后，`shares` 表仍无新行。
- 现有 turn 公开分享用例仍通过（抽函数后行为不变）。

前端：

- 卡片 `to` 为 `/r/{session_id}/{id}`；展开按钮不改变路由。
- `fetchTurn` 打上述 GET。

## 9. 数据流

```
/search 点命中
  → /r/{sessionId}/{messageId}
  → GET /api/sessions/{sessionId}/turns/{messageId}   // 不写 shares
  → 渲染一问一答
  →（可选）POST /api/sessions/{sessionId}/share/turn  // 才写 shares
  → 复制 origin + /s/{token}
```
