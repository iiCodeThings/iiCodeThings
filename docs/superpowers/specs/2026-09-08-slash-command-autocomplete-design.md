# 斜杠命令自动补全

日期：2026-09-08

输入 `/new-session` 不易发现。输入 `/` 时列出命令，随字符前缀筛选，点选或键盘选中后补全到输入框。

## 1. 目标

- 在 Composer 输入框做斜杠命令补全：输入 `/` 列出全部命令；继续输入则按前缀筛选；点选或 Enter 把命令写入输入框（末尾空格），不发送。
- 本轮命令表只有 `/new-session`。发送语义仍按现有 `parseNewSessionCommand`，不改后端。

## 2. 明确不做

- 不增加其它斜杠命令（含不把 `/search` 接进主界面）。
- 不改 `/new-session` 的发送/建会话/标题规则。
- 不把 textarea 换成富文本编辑器。
- 不做模糊匹配、拼音、历史命令。
- 不在正文中间的 `/` 上弹出（只处理整段仍在写命令的情况）。

## 3. 何时出现

对输入做 `trimStart()`（去掉开头空白，保留其余）：

- **命令草稿**：结果以 `/` 开头，且其中**没有空格**。此时显示列表（若有匹配项）。
- 否则不显示。包括：空输入、普通消息、`/new-session `、`/new-session 韦伯笔记`。

例：`/`、`  /n`、`/new-session` → 可显示。`/new-session ` → 关掉（开始写标题）。

## 4. 筛选

- 命令表：`[{ id: 'new-session', command: '/new-session', hint: '新建会话' }]`。
- 大小写敏感，按 `command` **前缀**匹配草稿字符串。`/` 匹配全部；`/n` 留下 `/new-session`；`/N`、`/foo` 无匹配。
- 无匹配则不渲染列表（当普通输入）。筛选结果变化时，高亮回到第一项。

## 5. 补全与键盘

- 点选或 Enter：把输入设为 `command + ' '`（如 `/new-session `），关掉列表，焦点留在 textarea。**不发送**。
- 列表打开时：默认高亮第一项；↑↓ 移动高亮，到顶/底停住不循环；Enter 补全高亮项（不发送）；Esc 关列表、输入不变。
- 因此：草稿为 `/new-session` 且列表开着时，第一次 Enter 变成 `/new-session `，第二次 Enter 才按现有逻辑发送建会话。
- 列表关闭后，Enter 仍走现有 `shouldSendOnKeydown` / `onSend`。
- 点列表外，或输入不再是命令草稿，关掉列表。
- 点选项：`mousedown.preventDefault`，避免 textarea 失焦。

## 6. 界面

- 列表浮在输入框**上方**，宽度跟 `.composer-box`，样式靠近现有会话菜单。
- 每行：命令字面量 + `hint`。窄屏行高至少约 44px。
- `role="listbox"` / `option`；高亮项 `aria-selected`；textarea 在列表打开时 `aria-expanded="true"`。

## 7. 测试

纯函数（不挂 Vue）：

- `slashCommandDraft(raw)`：命令草稿返回去掉开头空白后的字符串，否则 `null`。
- `matchSlashCommands(draft, commands)`：前缀、大小写、`/` 列出全部、无匹配空数组。
- `completeSlashCommand(command)`：返回末尾带一个空格的字符串。

现有 `parseNewSessionCommand` 与 Composer 发送路径单测仍通过。
