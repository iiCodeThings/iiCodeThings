# 会话置顶与发送快捷键

日期：2026-09-04

导航栏支持多会话置顶，并可把已置顶会话再次顶到最前。输入框 Enter 换行，Ctrl+Enter / Shift+Enter 发送。

## 1. 置顶

### 行为

- 可同时置顶多个会话。
- 每个会话在列表里只出现一次。
- 「置顶」：把该会话放到置顶区最前（未置顶则加入；已置顶则再点一次也是挪到最前）。
- 「取消置顶」：离开置顶区，回到下方未置顶列表，按 `updated_at` 倒序。
- 点选、重命名、删除不变。软删除的会话不再出现，其 `pinned_at` 无需清理。

### 列表

- 上方为置顶区（按 `pinned_at` 新→旧），下方为其余会话（按 `updated_at` 新→旧）。
- 置顶项有轻微标记（图标或样式），操作区始终提供「置顶」和「取消置顶」两个按钮；未置顶时「取消置顶」禁用或视觉变淡但可点则无效果——**未置顶时只显示置顶按钮，已置顶时两个都显示**，避免误点。

### 数据与接口

- `sessions.pinned_at`：可空 `DATETIME`。`NULL` = 未置顶。启动时 `migrate_schema` 补列（与 `deleted_at` 相同方式）。
- `GET /api/sessions` 排序：`pinned_at IS NOT NULL` 在前，同组内 `pinned_at DESC`，未置顶按 `updated_at DESC`。每项增加 `pinned: bool`（`pinned_at is not None`）。
- `POST /api/sessions/{id}/pin`：live session 将 `pinned_at` 设为当前时间；404「会话不存在」。
- `DELETE /api/sessions/{id}/pin`：live session 将 `pinned_at` 置 `NULL`；未置顶也返回 200。404 同上。
- 置顶 / 取消置顶 **不改** `updated_at`（用 Query `update` 显式写回原 `updated_at`，与重建标题相同）。
- 响应形状与现有 `_out` 一致，并含 `pinned`。

### 测试

- 多个会话置顶后列表顺序：后置顶的在前。
- 已置顶再 POST pin，该条排到置顶区第一，且 `updated_at` 不变。
- DELETE pin 后回到未置顶区，按 `updated_at` 排。
- 软删除 404。
- 未登录 401。

## 2. 发送快捷键

仅改前端 `Composer` 的 textarea：

- Enter：默认换行，不发送。
- Ctrl+Enter 或 Shift+Enter：调用现有 `onSend`。
- 点击「发送」仍发送。
- `event.isComposing` 或 `keyCode === 229` 时不发送（输入法组字）。
- 不绑定 Command+Enter。

现有空内容且无附件则 `onSend` 直接 return，快捷键同样遵守。

## 3. 明确不做

- 列表不出现同一会话的重复项。
- 不做拖拽排序。
- 不把置顶状态存到 localStorage。
- 不改 Mac Command 发送。
- 不改搜索页。
