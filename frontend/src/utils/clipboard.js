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
 * @param {string} s
 * @returns {string}
 */
function withoutTrailingNewlines(s) {
  return s.replace(/[\r\n]+$/, '');
}

/**
 * @param {Record<string, unknown>} row
 * @returns {string}
 */
function statusItemAgeSuffix(row) {
  const n = row.days_since_update;
  if (typeof n !== 'number' || Number.isNaN(n)) {
    return '';
  }
  const unit = n === 1 ? 'day' : 'days';
  return ` (${n} ${unit})`;
}

/**
 * @param {Record<string, unknown>} row
 * @returns {string}
 */
function statusItemReviewerSuffix(row) {
  const login =
    row.reviewer_login != null ? String(row.reviewer_login).trim() : '';
  return login ? ` (${login})` : '';
}

/**
 * Markdown lines: linked ``#number`` then space and title (for editors that read plain text).
 *
 * @param {Array<{ number: number, title?: string, html_url?: string, days_since_update?: number, reviewer_login?: string }>} items
 * @returns {string}
 */
export function formatStatusSectionClipboardMarkdown(items) {
  return withoutTrailingNewlines(
    (items || [])
      .map((row) => {
        const title = (row.title != null ? String(row.title) : '').trim();
        const reviewer = statusItemReviewerSuffix(row);
        const age = statusItemAgeSuffix(row);
        const url = (row.html_url != null ? String(row.html_url) : '').trim();
        if (!url) {
          return `#${row.number} ${title}${reviewer}${age}`.trim();
        }
        return `[#${row.number}](${url}) ${title}${reviewer}${age}`.trim();
      })
      .join('\n')
  );
}

/**
 * Minimal HTML (one line per item) so paste into Word / email keeps the number as a hyperlink.
 *
 * @param {Array<{ number: number, title?: string, html_url?: string, days_since_update?: number, reviewer_login?: string }>} items
 * @returns {string}
 */
export function formatStatusSectionClipboardHtml(items) {
  return (items || [])
    .map((row) => {
      const title = escapeHtmlText(
        (row.title != null ? String(row.title) : '').trim()
      );
      const reviewer = statusItemReviewerSuffix(row);
      const reviewerHtml = reviewer
        ? ` <strong>${escapeHtmlText(reviewer.trim())}</strong>`
        : '';
      const age = escapeHtmlText(statusItemAgeSuffix(row));
      const url = (row.html_url != null ? String(row.html_url) : '').trim();
      if (!url) {
        return `#${row.number} ${title}${reviewerHtml}${age}`;
      }
      const href = escapeHtmlAttr(url);
      return `<a href="${href}">#${row.number}</a> ${title}${reviewerHtml}${age}`;
    })
    .join('<br />');
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
 * @param {string} plain
 * @param {string} innerHtml
 * @returns {Promise<void>}
 */
async function copyRichClipboardContent(plain, innerHtml) {
  const htmlDoc = `<!DOCTYPE html><html><head><meta charset="utf-8" /></head><body>${innerHtml}</body></html>`;

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

/**
 * @param {{ number: number, title?: string, html_url?: string }} issue
 * @returns {string}
 */
export function formatIssueReferenceClipboardText(issue) {
  const title = (issue.title != null ? String(issue.title) : '').trim();
  return `#${issue.number} ${title}`.trim();
}

/**
 * @param {{ number: number, title?: string, html_url?: string }} issue
 * @returns {string}
 */
export function formatIssueReferenceClipboardHtml(issue) {
  const title = escapeHtmlText(
    (issue.title != null ? String(issue.title) : '').trim()
  );
  const url = (issue.html_url != null ? String(issue.html_url) : '').trim();
  const number = url
    ? `<a href="${escapeHtmlAttr(url)}">#${issue.number}</a>`
    : `#${issue.number}`;
  return `${number} ${title}`.trim();
}

/**
 * Copy an issue reference as rich HTML for document editors such as Google Docs.
 *
 * @param {{ number: number, title?: string, html_url?: string }} issue
 * @returns {Promise<void>}
 */
export async function copyIssueReferenceToClipboard(issue) {
  await copyRichClipboardContent(
    formatIssueReferenceClipboardText(issue),
    formatIssueReferenceClipboardHtml(issue)
  );
}

/**
 * Copy section rows with ``#number`` hyperlinked in HTML and Markdown link syntax in plain text.
 *
 * @param {Array<{ number: number, title?: string, html_url?: string, days_since_update?: number, reviewer_login?: string }>} items
 * @returns {Promise<void>}
 */
export async function copyStatusSectionToClipboard(items) {
  const plain = formatStatusSectionClipboardMarkdown(items);
  if (!plain) {
    return;
  }
  const innerHtml = formatStatusSectionClipboardHtml(items);
  await copyRichClipboardContent(plain, innerHtml);
}
