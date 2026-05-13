// Generated-by: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  copyTextToClipboard,
  copyStatusSectionToClipboard,
  formatStatusSectionClipboardHtml,
  formatStatusSectionClipboardMarkdown,
} from './clipboard';

describe('formatStatusSectionClipboardMarkdown', () => {
  it('uses Markdown links when html_url is present', () => {
    const text = formatStatusSectionClipboardMarkdown([
      {
        number: 42,
        title: 'Hello world',
        html_url: 'https://github.com/o/r/pull/42',
      },
      {
        number: 7,
        title: '  spaced  ',
        html_url: 'https://github.com/o/r/issues/7',
      },
    ]);
    expect(text).toBe(
      '[#42](https://github.com/o/r/pull/42) Hello world\n[#7](https://github.com/o/r/issues/7) spaced'
    );
  });

  it('falls back to #n title when url is missing', () => {
    expect(
      formatStatusSectionClipboardMarkdown([{ number: 1, title: 'No url' }])
    ).toBe('#1 No url');
  });

  it('returns empty string for empty list', () => {
    expect(formatStatusSectionClipboardMarkdown([])).toBe('');
    expect(formatStatusSectionClipboardMarkdown(null)).toBe('');
  });

  it('appends age suffix for PR backlog rows with days_since_update', () => {
    expect(
      formatStatusSectionClipboardMarkdown([
        {
          number: 50,
          title: 'Stale open',
          html_url: 'https://github.com/o/r/pull/50',
          days_since_update: 7,
        },
        {
          number: 51,
          title: 'One day',
          html_url: 'https://github.com/o/r/pull/51',
          days_since_update: 1,
        },
      ])
    ).toBe(
      '[#50](https://github.com/o/r/pull/50) Stale open (7 days)\n[#51](https://github.com/o/r/pull/51) One day (1 day)'
    );
  });
});

describe('formatStatusSectionClipboardHtml', () => {
  it('wraps the number in an anchor when html_url is present', () => {
    const html = formatStatusSectionClipboardHtml([
      { number: 1, title: 'A & B', html_url: 'https://github.com/o/r/pull/1' },
    ]);
    expect(html).toContain('<a href="https://github.com/o/r/pull/1">#1</a>');
    expect(html).toContain('A &amp; B');
  });

  it('escapes age suffix in HTML clipboard output', () => {
    const html = formatStatusSectionClipboardHtml([
      {
        number: 50,
        title: 'T',
        html_url: 'https://github.com/o/r/pull/50',
        days_since_update: 3,
      },
    ]);
    expect(html).toContain('T (3 days)');
  });
});

describe('copyTextToClipboard', () => {
  beforeEach(() => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
      writable: true,
    });
  });

  it('writes via the Clipboard API when available', async () => {
    await copyTextToClipboard('hello');
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('hello');
  });
});

describe('copyStatusSectionToClipboard', () => {
  beforeEach(() => {
    globalThis.ClipboardItem = class {
      constructor(data) {
        this._data = data;
      }
    };
  });

  it('uses clipboard.write with HTML and plain when supported', async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { write, writeText },
      configurable: true,
      writable: true,
    });

    await copyStatusSectionToClipboard([
      { number: 1, title: 'T', html_url: 'https://github.com/o/r/pull/1' },
    ]);

    expect(write).toHaveBeenCalledTimes(1);
    expect(writeText).not.toHaveBeenCalled();
  });

  it('falls back to writeText when write throws', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const write = vi.fn().mockRejectedValue(new Error('no'));
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { write, writeText },
      configurable: true,
      writable: true,
    });

    await copyStatusSectionToClipboard([
      { number: 1, title: 'T', html_url: 'https://github.com/o/r/pull/1' },
    ]);

    expect(writeText).toHaveBeenCalledWith(
      '[#1](https://github.com/o/r/pull/1) T'
    );
    warn.mockRestore();
  });
});
