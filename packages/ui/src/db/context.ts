/**
 * Database context — singleton adapter instance.
 *
 * In Web builds:  createSqlJsAdapter() (WASM)
 * In Tauri builds: createTauriAdapter()  (native SQLite)
 */

import { createSqlJsAdapter } from "./adapter-sqljs";
import type { DBAdapter } from "./adapter";

let _adapter: DBAdapter | null = null;
let _initPromise: Promise<void> | null = null;

/** Get or initialize the database adapter. Idempotent. */
export async function getDB(): Promise<DBAdapter> {
  if (_adapter) return _adapter;
  if (_initPromise) {
    await _initPromise;
    return _adapter!;
  }

  const adapter = createSqlJsAdapter();
  _initPromise = adapter.init().then(() => {
    _adapter = adapter;
    _initPromise = null;
  });

  await _initPromise;
  return adapter;
}

/** Close DB (call on app teardown). */
export async function closeDB(): Promise<void> {
  if (_adapter) {
    await _adapter.close();
    _adapter = null;
  }
}
