// Generated-by: Cursor
/** Today's date in the user's local timezone as ``YYYY-MM-DD`` (for ``<input type="date" />``). */
export const getLocalDateISOString = (d = new Date()) => {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

/**
 * Add signed calendar days to a local ``YYYY-MM-DD`` string (for ``<input type="date" />`` values).
 *
 * @param {string} dateIso
 * @param {number} deltaDays
 * @returns {string}
 */
export const addDaysToLocalDateISO = (dateIso, deltaDays) => {
  const [y, m, d] = dateIso.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + deltaDays);
  return getLocalDateISOString(dt);
};

export const getDaysSince = (dateString) => {
  if (!dateString) return 0;
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now - date);
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
};

export const formatDate = (dateString) => {
  if (!dateString) return 'No date';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};
