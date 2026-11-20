// Generated-by: Cline
import { findIssueFieldValue, issueFieldValueLabel } from './issueFields';
import { getIssueTypeKind } from './issueType';

const collator = new Intl.Collator(undefined, {
  sensitivity: 'base',
  numeric: true,
});

const TYPE_LABELS = {
  epic: 'Epic',
  feature: 'Feature',
  bug: 'Bug',
  task: 'Task',
};

const directionFactor = (direction) => (direction === 'desc' ? -1 : 1);

const textOrNull = (value) => {
  const text = String(value ?? '').trim();
  return text || null;
};

const compareNullableText = (left, right, direction) => {
  const a = textOrNull(left);
  const b = textOrNull(right);
  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;
  return collator.compare(a, b) * directionFactor(direction);
};

const compareNumber = (left, right, direction) =>
  (Number(left) - Number(right)) * directionFactor(direction);

const typeSortLabel = (issue) => {
  const kind = getIssueTypeKind(issue);
  if (kind === 'untyped') return null;
  if (kind === 'custom') return textOrNull(issue.type?.name);
  return TYPE_LABELS[kind] || null;
};

/**
 * Stable localStorage/header key for a planning issue field.
 */
export const planningFieldSortKey = (field) =>
  `field:${String(field?.name || '')
    .trim()
    .toLowerCase()}`;

const buildFieldContext = (field) => {
  const idRanks = new Map();
  const nameRanks = new Map();
  (field?.options || []).forEach((option, index) => {
    const priority = Number(option.priority);
    const rank = Number.isFinite(priority) ? priority : index + 1;
    if (option.id != null) idRanks.set(String(option.id), rank);
    const name = String(option.name || '')
      .trim()
      .toLowerCase();
    if (name) nameRanks.set(name, rank);
  });
  return { field, idRanks, nameRanks };
};

const fieldValueForSort = (issue, context) => {
  const value = findIssueFieldValue(
    issue.issue_field_values || [],
    context.field
  );
  if (!value) return null;
  const label = textOrNull(issueFieldValueLabel(value));
  if (!label) return null;
  const rank =
    (value.option_id != null
      ? context.idRanks.get(String(value.option_id))
      : undefined) ?? context.nameRanks.get(label.toLowerCase());
  return {
    rank: Number.isFinite(rank) ? rank : null,
    label,
  };
};

const compareFieldValue = (left, right, direction, context) => {
  const a = fieldValueForSort(left, context);
  const b = fieldValueForSort(right, context);
  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;
  if (a.rank != null && b.rank != null) {
    // GitHub option priority 1 is the highest/top option. Ascending means
    // low-to-high, so the numeric priority comparison is reversed.
    const comparison = a.rank - b.rank;
    return direction === 'asc' ? -comparison : comparison;
  }
  if (a.rank == null && b.rank == null) {
    return collator.compare(a.label, b.label) * directionFactor(direction);
  }
  return a.rank == null ? 1 : -1;
};

const compareColumn = (left, right, key, direction, fieldContexts) => {
  switch (key) {
    case 'type':
      return compareNullableText(
        typeSortLabel(left),
        typeSortLabel(right),
        direction
      );
    case 'author':
      return compareNullableText(
        left.user?.login,
        right.user?.login,
        direction
      );
    case 'title':
      return compareNullableText(left.title, right.title, direction);
    case 'number':
      return compareNumber(left.number, right.number, direction);
    default: {
      const context = fieldContexts.get(key);
      return context
        ? compareFieldValue(left, right, direction, context)
        : compareNumber(left.number, right.number, direction);
    }
  }
};

const sortNodes = (items, compare) =>
  (items || [])
    .map((item) => {
      if (!item.children) return { ...item };
      return { ...item, children: sortNodes(item.children, compare) };
    })
    .sort(compare);

/**
 * Sort a forest by a displayed issue field (or Number/Type/Author/Title).
 */
export const sortIssueForestByColumn = (items, spec = {}) => {
  const key = spec.key || 'number';
  const direction = spec.direction === 'desc' ? 'desc' : 'asc';
  const fieldContexts = new Map(
    (spec.fields || []).map((field) => [
      planningFieldSortKey(field),
      buildFieldContext(field),
    ])
  );
  const compare = (left, right) =>
    compareColumn(left, right, key, direction, fieldContexts) ||
    Number(left.number) - Number(right.number);
  return sortNodes(items, compare);
};

/**
 * Sort a forest by the configured label priority order.
 */
export const sortIssueForestByLabels = (items, sortOrder = []) => {
  const priorities = (sortOrder || [])
    .map((label) => String(label).trim().toLowerCase())
    .filter(Boolean);
  const bucket = (item) => {
    const labels = new Set(
      (item.labels || []).map((label) =>
        String(label?.name || label || '').toLowerCase()
      )
    );
    const index = priorities.findIndex((label) => labels.has(label));
    return index < 0 ? priorities.length : index;
  };
  const compare = (left, right) =>
    bucket(left) - bucket(right) || Number(left.number) - Number(right.number);
  return sortNodes(items, compare);
};

/**
 * Sort with the global Planning sort spec.
 */
export const sortIssueForestBySpec = (items, spec = {}) =>
  spec.mode === 'labels'
    ? sortIssueForestByLabels(items, spec.labelOrder || [])
    : sortIssueForestByColumn(items, {
        key: spec.key || 'number',
        direction: spec.direction || 'asc',
        fields: spec.fields || [],
      });
