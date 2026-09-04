# 个人学术对话系统 — 需求方案

个人自用的人与 AI 多轮对话工具，用来探讨社会学、人类学等学科话题。第一版做成通用聊天，不按学科做人设或资料库。部署在自己的 Ubuntu 私有云主机上。

## 1. 目标与约束

- **用户**：仅自己使用，单用户；需要用户名 + 密码登录，可修改密码。
- **部署**：Ubuntu Server 私有云；进程用 Supervisor 管理；MySQL 已安装。
- **数据库**：库名 `chat_db`；本机连接 `mysql -uroot chat_db`，无密码。
- **模型**：只对接 OpenAI 兼容 HTTP 接口（如 OpenAI / DeepSeek / 硅基流动 / 自建 vLLM）。切换模型 = 换 `base_url` + `api_key` + `model`。
- **技术栈**：后端 FastAPI（Python）+ 前端 Vue 3 SPA；Nginx 提供静态资源并反代 `/api`。

## 2. 功能需求

1. **切换大模型**：设置页维护多个 OpenAI 兼容端点；对话时用下拉框选择当前模型。
2. **Session 多轮对话**：每个 session 独立；发送时带上该 session 的全部历史（见 5.2）。
3. **持久化**：聊天记录写入 MySQL，包括助手的 reasoning（推理内容）。每条消息记录当时使用的模型展示名和 API model id（快照，不随设置改名而变）。
4. **浏览**：可查看 session 列表和某个 session 内的全部对话；右侧聊天记录向上无限滚动加载更早消息。
5. **搜索**：按关键词搜索对话；多个以空格分隔的词做 **AND 联合搜索**。
6. **附件**：输入框可上传图片与文档，模型能理解其内容。

## 3. 明确不做（第一版）

注册与多用户、学科入口/人设、RAG、移动端适配、消息编辑/对话分支、把历史 reasoning 再送给模型、Docker。

## 4. 页面结构

### 4.1 登录页

用户名 + 密码。失败时统一提示「用户名或密码错误」，不区分哪一项错。登录成功后进入主界面。

### 4.2 主界面（三块）

- **左栏上/中（导航）**
  - 搜索框：空格分隔、多词 AND。
  - 「新对话」按钮。
  - Session 列表：标题、更新时间；点击切换当前 session。点选只换右侧记录，左栏列表保持。
  - 当前模型下拉框：选项来自设置中已保存的模型。尚未配置任何模型时，下拉为空，发送对话须提示先去设置添加。
- **左栏底（输入）**：多行文本、发送、上传。输入框在左栏底部，不在聊天区底下。
- **右栏（聊天）**：当前 session 消息按时间正序。向上滚动加载更早记录。助手消息可展开查看 reasoning。生成过程以流式显示。

### 4.3 设置

左栏提供「设置」入口，进入独立路由 `/settings`（左栏仍在，可回到当前对话）。可：

- 增删改模型：`name`（展示名）、`base_url`、`api_key`、`model`（API 的 model id）、`supports_vision`（是否支持图片）。
- 修改登录密码：须提交旧密码 + 新密码；成功后 `token_version` 加一，已有 Cookie 全部失效，必须重新登录。

## 5. 交互细则

### 5.1 Session

- 新建 session 标题默认为「新对话」。
- 该 session 第一条用户消息发送成功后，若标题仍是「新对话」，则自动命名：优先用正文去掉换行后截断为最多 40 个字符；正文为空则用第一个附件的原文件名（去掉扩展名）截断到 40 字符。
- 用户可在列表中改标题、删除 session（同时删除其消息和附件文件）。

### 5.2 上下文

- 发送时组装该 session 内全部 `user` / `assistant` 的 `content`，以及对应附件（图片按 vision 格式，文档用抽取文本）。
- **不把**历史 `reasoning` 回传给模型。
- 默认全量发送。若上游返回上下文超长错误：从最早的 user/assistant 轮次开始丢弃，保留最近轮次，并在前端提示「上下文过长，已截断较早消息」。本轮附件不得因截断被丢掉。

### 5.3 模型快照

用户消息与助手消息都写入当时选中的 `model_name`（展示名）和 `model`（API id）。Session 中途换模型时，每一轮都能看出用的是哪个模型。

### 5.4 流式与失败

- 使用 SSE 推送：文本增量、reasoning 增量、结束、错误。
- 用户消息先入库再请求模型。若流式失败或中断：不写入半截助手消息；前端展示错误；用户可再发送一条新消息重试（第一版不做「对同一条用户消息覆盖再生成」）。

### 5.5 搜索

- 查询字符串按空格分词，去掉空 token。
- 空查询：行为与普通 session 列表相同（按 `updated_at` 倒序）。
- 非空：每个词都必须在该 session 上命中至少一次。命中位置 = session 标题 **或** 该 session 任意一条 `messages.content`。词可以分散在标题和不同消息里。
- 不搜索 `reasoning`，不搜索附件 `extracted_text`。
- 返回 session 列表，每项含：`id`、`title`、`updated_at`、`snippet`（含关键词的片段）、`hit_message_id`（命中来自标题则为空）。点击进入该 session；若有 `hit_message_id`，右侧滚动到该消息。

### 5.6 附件

| 类型 | 扩展名 | 处理 |
|------|--------|------|
| 图片 | `.jpg` `.jpeg` `.png` `.webp` | 存盘；按 OpenAI vision 的 image 内容发给模型 |
| 文档 | `.txt` `.md` `.doc` `.docx` | 存盘并抽文本，写入 `extracted_text`，拼进本轮用户文本 |

- 第一版同时接受 `.docx`（用 `python-docx` 抽文本）；`.doc` 在 Ubuntu 上用 **antiword** 抽文本。抽失败：提示用户，原文件仍保存，本轮不把空文本当上下文。
- 不在允许列表内的类型：拒绝上传。
- 单文件大小上限 **20MB**，可在配置中修改。
- 文本与文件都为空：HTTP 400，不写消息。
- 若本轮带了图片且所选模型 `supports_vision` 不为真：不调用上游，返回明确错误，提示更换支持视觉的模型。

## 6. 数据模型（MySQL `chat_db`）

### `users`

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `username` | 唯一 |
| `password_hash` | 单向哈希 |
| `token_version` | 整数，默认 0；改密后加一 |
| `created_at` / `updated_at` | 时间 |

登录 Cookie 为签名 HttpOnly，载荷含 `user_id` 与 `token_version`；二者与库中不一致则视为未登录。

`APP_USERNAME`、`APP_PASSWORD`、`SESSION_SECRET` 为启动必填；缺一则进程拒绝启动。首次启动若 `users` 为空则插入该默认账号；已有用户则不重复插入。

### `llm_models`

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `name` | 展示名 |
| `base_url` | OpenAI 兼容接口根路径 |
| `api_key` | 仅存数据库，不进 git |
| `model` | API 的 model id |
| `supports_vision` | 布尔，默认否；发送图片前检查 |
| `sort_order` | 下拉排序 |
| `created_at` / `updated_at` | 时间 |

### `sessions`

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `title` | 默认「新对话」 |
| `created_at` / `updated_at` | 有新消息时更新 `updated_at` |

### `messages`

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `session_id` | 外键，级联删除 |
| `role` | `user` 或 `assistant` |
| `content` | 正文 |
| `reasoning` | 助手推理内容，可空 |
| `model_name` | 展示名快照 |
| `model` | API model id 快照 |
| `created_at` | 时间 |

索引：`(session_id, id)`，供按 id 向前翻页。

### `attachments`

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `message_id` | 外键，级联删除 |
| `kind` | `image` 或 `document` |
| `original_filename` | 原文件名 |
| `mime_type` | MIME |
| `storage_path` | 服务器磁盘路径 |
| `extracted_text` | 文档抽出的正文；图片为空 |
| `created_at` | 时间 |

文件本体放主机目录（默认 `/var/lib/iicode-chat/uploads`），库中只存路径和抽取文本。删除 session 或消息时删除对应文件。

检索不另建表：对标题和 `messages.content` 做多词 AND + `LIKE`。

## 7. 后端接口

除登录外均需有效登录 Cookie（HttpOnly）。未登录 API 返回 `401`，前端跳转登录页。

| 用途 | 方法 | 路径 |
|------|------|------|
| 登录 | POST | `/api/auth/login` |
| 登出 | POST | `/api/auth/logout` |
| 修改密码 | POST | `/api/auth/password` |
| Session 列表 | GET | `/api/sessions` |
| 新建 session | POST | `/api/sessions` |
| 改标题 | PATCH | `/api/sessions/{id}` |
| 删除 session | DELETE | `/api/sessions/{id}` |
| 消息分页 | GET | `/api/sessions/{id}/messages?before_id=&limit=` |
| 发送（SSE） | POST | `/api/sessions/{id}/messages`（multipart：`content`、`model_id`、文件） |
| 搜索 | GET | `/api/search?q=` |
| 模型列表与维护 | GET/POST/PATCH/DELETE | `/api/models` |

GET 列表不返回完整 `api_key`，只返回掩码（如末 4 位）。POST/PATCH 可写入新密钥。

消息分页：按 `id` 倒序取 `limit` 条（默认 50，最大 100）。`before_id` 为空表示最新一页。前端反转后正序渲染。

发送流程：

1. 鉴权；校验 session 存在。
2. 校验：已选择存在的模型；文本与文件不同时为空；若有图片则该模型 `supports_vision` 为真。失败则 HTTP 错误，不写库。
3. 落库用户消息（正文、附件、模型快照）。
4. 处理附件（存盘、抽文本或准备 vision 部分）。
5. 组装上下文并请求上游 `chat.completions`（`stream: true`）。
6. SSE 推送给前端。
7. 完整助手消息入库（`content`、`reasoning`、同一套模型快照）；更新 `sessions.updated_at`；必要时按 5.1 更新标题。

## 8. 错误处理

- 上游超时 / 4xx / 5xx：SSE 以错误事件结束，展示可读信息（含上游摘要）；用户消息保留。
- 附件类型非法、超过大小、空发送、未选模型：HTTP 4xx，不写消息。
- 带图片但 `supports_vision` 为否：HTTP 400，不写消息、不调用上游。
- Cookie 无效、过期，或 `token_version` 不匹配：`401`。

## 9. 部署

- **前端**：Vue 3 + Vite 构建为静态文件，Nginx 托管。
- **后端**：venv + uvicorn 运行 FastAPI。
- **Nginx**：站点根目录为前端 dist；`/api` 反代到 uvicorn；上传与 SSE 关闭缓冲（`proxy_buffering off`；适当加大 `client_max_body_size`，如 25m）。
- **Supervisor**：只管理 uvicorn（开机启动、异常退出重启、stdout/stderr 日志）。Nginx 仍用系统自带服务。
- **配置**：环境变量或本地配置文件（不提交 git）。必填：`APP_USERNAME`、`APP_PASSWORD`、`SESSION_SECRET`。其余：MySQL（默认 `root`、空密码、库 `chat_db`、主机 `127.0.0.1`）、上传目录、单文件大小上限。
- **权限**：Supervisor 所跑用户对上传目录可写。
- 单机直装，不用 Docker。

## 10. 验收标准

1. 用默认账号登录；修改密码后旧密码失效，新密码可登录。
2. 设置中添加至少两个 OpenAI 兼容模型；对话中可切换；库中每条消息能看到当时的 `model_name` 与 `model`。
3. 同一 session 多轮，后一轮能引用前面的内容；reasoning 可展开，且不会作为后续请求的上下文。
4. 右栏向上滚动能加载更早消息；刷新页面后记录仍在。
5. 上传 png 与一份 md/txt，模型能基于图片或文档内容回答；doc/docx 能抽出文字。
6. 搜索 `词A 词B` 只返回两个词都命中的 session。
7. 在 Supervisor 中停止再启动 uvicorn 后，Nginx 打开页面仍能完成一轮对话。

## 11. 架构摘要

单机两进程：浏览器加载 Vue SPA；API 与模型代理在 FastAPI。FastAPI 读写 `chat_db`、本地上传目录，并把 OpenAI 兼容的流式响应转成 SSE。Supervisor 保证 API 进程存活；Nginx 对外提供 80/443。
