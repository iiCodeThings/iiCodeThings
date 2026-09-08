# 斜杠命令自动补全

日期：2026-09-08

输入 `/new-session` 不易发现。输入 `/` 时列出命令，随字符前缀筛选，点选或键盘选中后补全到输入框。

## 1. 目标

- 在 Composer 输入框做斜杠命令补全：输入 `/` 列出全部命令；继续输入则按前缀筛选；点选或 Enter 把命令写入输入框（末尾空格），不发送。
- 命令表两条：`/new-session`（新建会话）、`/search`（跳转到 `/search` 页面）。
- `/new-session` 发送语义仍按现有 `parseNewSessionCommand`。`/search` 发送时前端路由到 `/search`，不调模型。都不改后端。

## 2. 明确不做

- 不增加这两条以外的斜杠命令。
- 不改 `/new-session` 的建会话/标题规则。
- `/search` 只跳转到搜索页，不把输入框剩余文字填进搜索框，不改搜索页本身。
- 不把 textarea 换成富文本编辑器。
- 不做模糊匹配、拼音、历史命令。
- 不在正文中间的 `/` 上弹出（只处理整段仍在写命令的情况）。

## 3. 何时出现

对输入做 `trimStart()`（去掉开头空白，保留其余）：

- **命令草稿**：结果以 `/` 开头，且其中**没有空格**。此时显示列表（若有匹配项）。
- 否则不显示。包括：空输入、普通消息、`/new-session `、`/search `、带标题/其它参数的命令。

例：`/`、`  /n`、`/new-session`、`/s` → 可显示。`/new-session `、`/search ` → 关掉。

## 4. 筛选

命令表（顺序固定）：

- `{ id: 'new-session', command: '/new-session', hint: '新建会话' }`
- `{ id: 'search', command: '/search', hint: '打开搜索' }`

大小写敏感，按 `command` **前缀**匹配草稿字符串。

- `/` → 两条都列出（先 `/new-session`，后 `/search`）
- `/n` → 只留 `/new-session`
- `/s` → 只留 `/search`
- `/N`、`/foo` → 无匹配，不渲染列表

筛选结果变化时，高亮回到第一项。

## 5. 补全与键盘

- 点选或 Enter：把输入设为 `command + ' '`（如 `/new-session ` 或 `/search `），关掉列表，焦点留在 textarea。**不发送、不跳转**。
- 列表打开时：默认高亮第一项；↑↓ 移动高亮，到顶/底停住不循环；Enter 补全高亮项（不发送）；Esc 关列表、输入不变。
- 因此：草稿为某条完整命令且列表开着时，第一次 Enter 补全并加上尾空格，第二次 Enter 才执行该命令。
- 列表关闭后，Enter 仍走现有 `shouldSendOnKeydown` / `onSend`。
- 点列表外，或输入不再是命令草稿，关掉列表。
- 点选项：`mousedown.preventDefault`，避免 textarea 失焦。

## 6. 发送时怎么执行

发送前对正文 `trim()`：

- 以 `/new-session` 开头：现有逻辑（建会话，可选标题；不调模型、不传附件、不要求已选模型）。
- 否则若以 `/search` 开头：`router.push('/search')`，清空输入，不调模型、不传附件、不要求已选模型。剩余文字忽略（`/search`、`/search   `、`/search foo`、`/searchfoo` 都只跳转，不带查询参数）。
- 其它输入：普通发消息，仍要选模型。

两条命令都大小写敏感。先判断 `/new-session`（更长短前缀不会冲突：`/search` 不是 `/new-session` 前缀）。

## 7. 界面

- 列表浮在输入框**上方**，宽度跟 `.composer-box`，样式靠近现有会话菜单。
- 每行：命令字面量 + `hint`。窄屏行高至少约 44px。
- `role="listbox"` / `option`；高亮项 `aria-selected`；textarea 在列表打开时 `aria-expanded="true"`。
- Composer 仍只出现在对话页（`/`）。从这里发送 `/search` 会离开 AppShell，进入现有独立路由 `/search`。

## 8. 测试

纯函数（不挂 Vue）：

- `slashCommandDraft(raw)`：命令草稿返回去掉开头空白后的字符串，否则 `null`。
- `matchSlashCommands(draft, commands)`：`/` 列出两条、`/n` / `/s` 各一条、大小写、无匹配空数组。
- `completeSlashCommand(command)`：返回末尾带一个空格的字符串。
- `parseSearchCommand(raw)`：非命令返回 `null`；以 `/search` 开头返回真值（剩余文字可忽略）。

现有 `parseNewSessionCommand` 与 Composer 发送路径单测仍通过。
