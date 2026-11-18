// Generated-by: Codex
import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  cachedQuery,
  createMetadataCache,
  invalidateQueries,
  setQueryRepository,
} from './queryCache';

const deferred = () => {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
};
afterEach(() => vi.useRealTimers());

describe('shared queries', () => {
  it('coalesces in-flight reads and caches valid empty responses', async () => {
    const loader = vi.fn().mockResolvedValue([]);
    const a = cachedQuery('/labels', loader);
    expect(cachedQuery('/labels', loader)).toBe(a);
    expect(await a).toEqual([]);
    expect(await cachedQuery('/labels', loader)).toEqual([]);
    expect(loader).toHaveBeenCalledTimes(1);
  });

  it('expires metadata and isolates repositories and milestone state', async () => {
    vi.useFakeTimers();
    const loader = vi.fn().mockResolvedValue([]);
    setQueryRepository('a/b');
    await cachedQuery('/milestones?state=open', loader);
    await cachedQuery('/milestones?state=closed', loader);
    await cachedQuery('/milestones?state=open', loader);
    expect(loader).toHaveBeenCalledTimes(2);
    vi.advanceTimersByTime(30001);
    await cachedQuery('/milestones?state=open', loader);
    setQueryRepository('a/c');
    await cachedQuery('/milestones?state=open', loader);
    expect(loader).toHaveBeenCalledTimes(4);
  });

  it('does not publish an old read after a mutation', async () => {
    const old = deferred();
    const loader = vi
      .fn()
      .mockReturnValueOnce(old.promise)
      .mockResolvedValue(['fresh']);
    const pending = cachedQuery('/issues/1', loader);
    await Promise.resolve();
    invalidateQueries();
    old.resolve(['stale']);
    expect(await pending).toEqual(['fresh']);
    expect(await cachedQuery('/issues/1', loader)).toEqual(['fresh']);
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it('explicit refresh bypasses pending reads and older consumers receive the new result', async () => {
    const old = deferred();
    const loader = vi
      .fn()
      .mockReturnValueOnce(old.promise)
      .mockResolvedValue(['new']);
    const pending = cachedQuery('/sdlc/dashboard', loader);
    await Promise.resolve();
    expect(
      await cachedQuery('/sdlc/dashboard', loader, { force: true })
    ).toEqual(['new']);
    old.resolve(['old']);
    expect(await pending).toEqual(['new']);
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it('does not loop or cache failures, and allows an explicit later retry', async () => {
    const loader = vi
      .fn()
      .mockRejectedValueOnce(new Error('failed'))
      .mockResolvedValue([]);
    await expect(cachedQuery('/comments/1', loader)).rejects.toThrow('failed');
    expect(loader).toHaveBeenCalledTimes(1);
    expect(await cachedQuery('/comments/1', loader)).toEqual([]);
  });

  it('tracks valid empty metadata and invalidates it after writes', () => {
    const cache = createMetadataCache();
    expect(cache.loaded).toBe(false);
    cache.data = [];
    expect(cache.loaded).toBe(true);
    invalidateQueries();
    expect(cache.loaded).toBe(false);
    cache.data = ['private'];
    setQueryRepository('another/repo');
    expect(cache.data).toEqual([]);
    expect(cache.loaded).toBe(false);
  });
});
