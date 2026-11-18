// Generated-by: Codex
// Short-lived, repository-scoped read cache. Mutations invalidate pending writes
// to the cache as well, so an older read cannot repopulate it after a mutation.
const entries = new Map();
let repository = '';
let generation = 0;

const trimCompletedEntries = () => {
  for (const [key, entry] of entries) {
    if (entries.size <= 256) break;
    if (!entry.promise) entries.delete(key);
  }
};

export const invalidateQueries = (prefix = '') => {
  generation += 1;
  for (const key of entries.keys()) {
    if (key.startsWith(`${repository}:${prefix}`)) entries.delete(key);
  }
};

export const setQueryRepository = (repo) => {
  if (repository !== repo) {
    repository = repo;
    generation += 1;
    entries.clear();
  }
};

export const cachedQuery = (
  key,
  loader,
  { ttl = 30000, force = false, revalidate = false } = {}
) => {
  const scopedKey = `${repository}:${key}`;
  const previous = entries.get(scopedKey);
  // Force bypasses both completed and in-flight reads: Apply/Refresh is an
  // explicit request for a new observation, even with unchanged parameters.
  if (!force && previous) {
    if (previous.promise) return previous.promise;
    if (!revalidate && previous.expires > Date.now())
      return Promise.resolve(previous.data);
  }
  const revision = generation;
  const entry = {};
  entry.promise = Promise.resolve()
    .then(loader)
    .then(
      (data) => {
        if (generation !== revision || entries.get(scopedKey) !== entry) {
          // A write or newer forced read superseded this response. Existing
          // consumers rejoin a current read, so local UI caches cannot revive it.
          if (entries.get(scopedKey) === entry) entries.delete(scopedKey);
          return cachedQuery(key, loader, { ttl });
        }
        entry.data = data;
        entry.expires = Date.now() + ttl;
        entry.promise = null;
        trimCompletedEntries();
        return data;
      },
      (error) => {
        if (generation !== revision || entries.get(scopedKey) !== entry) {
          if (entries.get(scopedKey) === entry) entries.delete(scopedKey);
          return cachedQuery(key, loader, { ttl });
        }
        entries.delete(scopedKey);
        throw error;
      }
    );
  entries.set(scopedKey, entry);
  trimCompletedEntries();
  return entry.promise;
};

export const createMetadataCache = () => {
  let data = [];
  let loadedAt = null;
  let scope = repository;
  let revision = generation;
  return {
    get data() {
      return scope === repository ? data : [];
    },
    set data(value) {
      data = value;
      loadedAt = Date.now();
      scope = repository;
      revision = generation;
    },
    get loaded() {
      return (
        scope === repository &&
        revision === generation &&
        loadedAt !== null &&
        Date.now() - loadedAt < 30000
      );
    },
    loading: false,
    error: null,
    promise: null,
    clear() {
      data = [];
      loadedAt = null;
      this.loading = false;
      this.error = null;
      this.promise = null;
    },
  };
};
