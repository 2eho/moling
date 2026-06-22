interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

interface CacheOptions {
  ttl?: number;
  maxSize?: number;
}

export class DedupCache {
  private store = new Map<string, CacheEntry<any>>();
  private pending = new Map<string, Promise<any>>();
  private ttl: number;
  private maxSize: number;

  constructor(options: CacheOptions = {}) {
    this.ttl = options.ttl ?? 30_000;
    this.maxSize = options.maxSize ?? 50;
  }

  get<T>(key: string): T | undefined {
    const entry = this.store.get(key);
    if (!entry) return undefined;
    if (Date.now() - entry.timestamp > this.ttl) {
      this.store.delete(key);
      return undefined;
    }
    return entry.data;
  }

  set<T>(key: string, data: T): void {
    if (this.store.size >= this.maxSize) {
      const firstKey = this.store.keys().next().value;
      if (firstKey) this.store.delete(firstKey);
    }
    this.store.set(key, { data, timestamp: Date.now() });
  }

  /** GET 请求去重：同一时间同一 key 只发一次请求 */
  async dedupe<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
    // 先查缓存
    const cached = this.get<T>(key);
    if (cached !== undefined) return cached;

    // 去重：如果已有 pending 请求，等待结果
    if (this.pending.has(key)) {
      return this.pending.get(key)!;
    }

    // 发起新请求
    const promise = fetcher()
      .then((data) => {
        this.set(key, data);
        this.pending.delete(key);
        return data;
      })
      .catch((error) => {
        this.pending.delete(key);
        throw error;
      });

    this.pending.set(key, promise);
    return promise;
  }

  clear(): void {
    this.store.clear();
    this.pending.clear();
  }

  invalidate(key: string): void {
    this.store.delete(key);
  }
}

export const apiCache = new DedupCache();
