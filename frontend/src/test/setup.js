// Generated-by: Cursor
import { expect, afterEach, beforeEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import { invalidateQueries } from '../utils/queryCache';
beforeEach(() => invalidateQueries());

afterEach(() => {
  cleanup();
});

// Node 27 may expose an unconfigured global Web Storage object in jsdom.
// Use an isolated Web Storage fallback when jsdom cannot supply one.
// Assisted-by: Codex
if (!globalThis.localStorage) {
  const values = new Map();
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: {
      getItem: (key) => values.get(String(key)) ?? null,
      setItem: (key, value) => values.set(String(key), String(value)),
      removeItem: (key) => values.delete(String(key)),
      clear: () => values.clear(),
      key: (index) => [...values.keys()][index] ?? null,
      get length() {
        return values.size;
      },
    },
  });
}
