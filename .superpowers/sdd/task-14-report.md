# Task 14 Report: 三栏壳、Session 列表、设置页、输入框

## TDD

### RED
- Created `frontend/src/api.test.js`: `acceptAttr` contains `.png` and `.md`
- `npm test` → **FAIL** `acceptAttr` undefined (`toContain` invalid for undefined)

### GREEN
- Exported `acceptAttr = '.jpg,.jpeg,.png,.webp,.txt,.md,.doc,.docx'` from `api.js`
- Added API helpers: `listSessions` / `createSession` / `patchSession` / `deleteSession` / `listModels` / `createModel` / `updateModel` / `deleteModel` / `changePassword`
- `AppShell.vue`: left nav (search, 新对话, session list, model `<select>`, 设置 link) + bottom `Composer`; right `<RouterView>`
- `Composer.vue`: textarea, file input with `acceptAttr`, send alerts「请先在设置中添加模型」when no model
- `ChatView.vue`: placeholder「选择或新建对话」; `currentId` owned by AppShell (select / createSession)
- `SettingsView.vue`: model CRUD form fields + password form; nested under AppShell via routes
- CSS shell layout per brief; routes `/` + `/settings` children of AppShell
- `npm test` → **PASS** (2)
- `npm run build` → **PASS**

## Commit
`feat: add three-pane shell, session list, settings, and composer`

## Files
- `frontend/src/api.js`, `frontend/src/api.test.js`
- `frontend/src/components/AppShell.vue`, `Composer.vue`
- `frontend/src/views/ChatView.vue`, `SettingsView.vue` (removed `HomeView.vue`)
- `frontend/src/main.js`, `frontend/src/styles.css`

## Concerns
- Search box only client-filters session titles; `/api/search` wired in Task 15
- Composer send is stub until Task 15 streaming
- `currentId` lives in AppShell (not ChatView) so settings navigation keeps selection

## Review fix (Important)

### Code change
`AppShell.vue`:
1. `watch(route.path)` — leaving `/settings` reloads models so the select reflects CRUD done on settings.
2. `loadModels` — if selection empty or missing from list, default to first model; clear selection when `models.length === 0` (Composer alert only then).

### Re-verify
```
cd frontend && npm test && npm run build
```

```
> frontend@1.0.0 test
> vitest run

 Test Files  2 passed (2)
      Tests  2 passed (2)
   Duration  344ms

> frontend@1.0.0 build
> vite build

✓ 28 modules transformed.
✓ built in 364ms
```

**Result:** PASS (2 tests) + build OK

### Commit
`fix: refresh models and default selection in AppShell`
