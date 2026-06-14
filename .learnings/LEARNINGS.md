# Learnings

Corrections, insights, and knowledge gaps captured during development.

---

## [LRN-20260614-001] best_practice

**Logged**: 2026-06-14T16:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
`from app.dao import user_dao` imports a singleton UserDAO **instance**, not the module. Calling `user_dao.UserDAO()` raises `'UserDAO' object has no attribute 'UserDAO'`.

### Details
In `app/dao/__init__.py`, `user_dao = UserDAO()` creates a singleton instance. When services do `from app.dao import user_dao`, they get the instance. Then `user_dao.UserDAO()` tries `.UserDAO` attribute on the instance, which doesn't exist. Fix: just use `user_dao` directly.

### Suggested Action
Search all service files for `user_dao.UserDAO()` pattern using grep.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: auth_service.py (lines 250, 293)
- **Notes**: Changed `dao = user_dao.UserDAO()` to `dao = user_dao`

### Metadata
- Source: runtime error
- Related Files: app/dao/__init__.py, app/service/auth_service.py
- Tags: dao, singleton, import, common_mistake

---

## [LRN-20260614-002] insight

**Logged**: 2026-06-14T16:20:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Windows + aiosqlite + async SQLAlchemy has a known greenlet issue that cannot be fully patched. The `greenlet_spawn` monkey patch works for some operations but fails when `aiosqlite.connect()` (inherently async) is called from within the thread pool executor.

### Details
The greenlet patch in `dependencies.py` replaces `greenlet_spawn` with a thread pool executor. This works for sync-to-async bridging but fails for async-to-async calls like `aiosqlite` connection. The fix for `get_current_user` was to switch to `SyncSession` (sync DB), which completely avoids the async path.

### Suggested Action
For Windows development, either:
1. Switch all DB operations to sync sessions
2. Use a sync SQLite driver (e.g., pysqlite)
3. Document that production should run on Linux

### Metadata
- Source: runtime testing
- Related Files: app/dependencies.py, app/dao/base_dao.py
- Tags: windows, greenlet, aiosqlite, async

---

## [LRN-20260614-003] best_practice

**Logged**: 2026-06-14T16:20:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
Card service `get_draw_history()` method existed but router returned hardcoded `[]`. Router TODO comment said "implement get_draw_history in service" but the method was already implemented.

### Details
The router at `app/router/card.py:69` had `# TODO: implement get_draw_history in service` and returned `[]`. But `card_service.get_draw_history()` at `card_service.py:322` was fully implemented. Fix: simply call the service method.

### Suggested Action
Search for other routers with TODO comments that reference already-implemented service methods.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: app/router/card.py

### Metadata
- Source: code audit
- Related Files: app/router/card.py, app/service/card_service.py
- Tags: dead_code, router, stub

---

## [LRN-20260614-004] best_practice

**Logged**: 2026-06-14T17:05:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
Pydantic v2 `populate_by_name=True` + `from_attributes=True` causes SQLAlchemy ORM relation lists to be passed as field values, breaking field validation.

### Details
When `model_config = {"from_attributes": True, "populate_by_name": True}`, Pydantic tries both `validation_alias` and field name during population. For a field like `chapters: int` with `validation_alias="chapter_count"`, when the ORM object has a `chapters` relationship list but no `chapter_count` attribute, Pydantic falls back to passing the relationship list to the `chapters` field. This causes `ValidationError` because `list` is not `int`.

### Suggested Action
For MVP, remove `populate_by_name=True` and add a `@field_validator("chapters", mode="before")` to convert list→int. Also, never type ORM id fields as `str` when SQLAlchemy returns `int` — use `int`.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: app/schemas/project.py
- **Notes**: Removed `populate_by_name=True`, added field_validator for chapters, changed `id: str`→`id: int`

### Metadata
- Source: e2e testing (500 error on project creation)
- Related Files: app/schemas/project.py
- Tags: pydantic, schema, validation, common_mistake

---

## [LRN-20260614-005] pitfall

**Logged**: 2026-06-14T17:05:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
Frontend mock data (`mockTimelines`) uses a flat structure with `event: string` while the `VaultTimeline` interface expects `events: VaultTimelineEvent[]`. This mismatch causes TypeScript error when mock code tries `t.events`.

### Details
The mock timeline data at `src/mock/vault.ts:79` stores individual timeline entries with `event` (singular string), but `@/lib/types.ts:148` defines `VaultTimeline.events` as `VaultTimelineEvent[]`. When mock code at `index.ts:950` accesses `t.events`, TypeScript reports it doesn't exist because the mock data uses a different shape.

### Suggested Action
Use `map()` to convert mock data to the correct shape rather than `flatMap()`, since each mock entry IS a single event.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: src/mock/index.ts

### Metadata
- Source: tsc type checking
- Related Files: src/mock/vault.ts, src/mock/index.ts, src/lib/types.ts
- Tags: typescript, mock, type_mismatch

---
