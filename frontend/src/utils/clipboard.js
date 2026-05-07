// Generated-by: Cursor
/**
 * @param {string} s
 * @returns {string}
 */
function escapeHtmlText(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * @param {string} s
 * @returns {string}
 */
function escapeHtmlAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

/**
 * Markdown lines: linked ``#number`` then space and title (for editors that read plain text).
 *
 * @param {Array<{ number: number, title?: string, html_url?: string }>} items
 * @returns {string}
 */
export function formatStatusSectionClipboardMarkdown(items) {
  return (items || [])
    .map((row) => {
      const title = (row.title != null ? String(row.title) : '').trim();
      const url = (row.html_url != null ? String(row.html_url) : '').trim();
      if (!url) {
        return `#${row.number} ${title}`.trim();
      }
      return `[#${row.number}](${url}) ${title}`.trim();
    })
    .join('\n');
}

/**
 * Minimal HTML (one line per item) so paste into Word / email keeps the number as a hyperlink.
 *
 * @param {Array<{ number: number, title?: string, html_url?: string }>} items
 * @returns {string}
 */
export function formatStatusSectionClipboardHtml(items) {
  return (items || [])
    .map((row) => {
      const title = escapeHtmlText(
        (row.title != null ? String(row.title) : '').trim()
      );
      const url = (row.html_url != null ? String(row.html_url) : '').trim();
      if (!url) {
        return `#${row.number} ${title}`;
      }
      const href = escapeHtmlAttr(url);
      return `<a href="${href}">#${row.number}</a> ${title}`;
    })
    .join('<br />\n');
}

/**
 * @param {string} text
 * @returns {Promise<void>}
 */
export async function copyTextToClipboard(text) {
  if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
    return;
  }
  await navigator.clipboard.writeText(text);
}

/**
 * Copy section rows with ``#number`` hyperlinked in HTML and Markdown link syntax in plain text.
 *
 * @param {Array<{ number: number, title?: string, html_url?: string }>} items
 * @returns {Promise<void>}
 */
export async function copyStatusSectionToClipboard(items) {
  const plain = formatStatusSectionClipboardMarkdown(items);
  if (!plain) {
    return;
  }
  const innerHtml = formatStatusSectionClipboardHtml(items);
  const htmlDoc = `<!DOCTYPE html><html><body><meta charset="utf-8"><div>${innerHtml}</div></body></html>`;

  if (
    typeof navigator !== 'undefined' &&
    navigator.clipboard?.write &&
    typeof ClipboardItem !== 'undefined'
  ) {
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/plain': new Blob([plain], { type: 'text/plain' }),
          'text/html': new Blob([htmlDoc], { type: 'text/html' }),
        }),
      ]);
      return;
    } catch (e) {
      console.warn('clipboard.write failed, falling back to text only', e);
    }
  }
  await copyTextToClipboard(plain);
}
