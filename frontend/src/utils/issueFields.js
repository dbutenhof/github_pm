// Generated-by: Cline
/**
 * Repository issue fields shown as editable Planning board columns.
 */
export const PLANNING_ISSUE_FIELD_NAMES = ['Priority', 'Effort'];

/**
 * Pick the configured Planning fields from a repository issue-field catalog.
 */
export const findPlanningIssueFields = (fields = []) =>
  PLANNING_ISSUE_FIELD_NAMES.map((name) =>
    (fields || []).find(
      (field) =>
        String(field?.name || '').toLowerCase() === name.toLowerCase() &&
        field?.data_type === 'SINGLE_SELECT'
    )
  ).filter(Boolean);

/**
 * Find the value currently assigned to an issue for a field definition.
 */
export const findIssueFieldValue = (values = [], field) => {
  if (!field) return null;
  const fieldName = String(field.name || '').toLowerCase();
  return (
    (values || []).find(
      (value) =>
        value?.field_id === field.id ||
        String(value?.field_name || '').toLowerCase() === fieldName
    ) || null
  );
};

const OPTION_COLORS = {
  GRAY: '#6e7781',
  BLUE: '#0969da',
  GREEN: '#2da44e',
  YELLOW: '#bf8700',
  ORANGE: '#bc4c00',
  RED: '#cf222e',
  PINK: '#bf3989',
  PURPLE: '#8250df',
};

/**
 * Map a GitHub single-select option color name to a display color.
 */
export const issueFieldOptionColor = (color) =>
  OPTION_COLORS[String(color || '').toUpperCase()] || OPTION_COLORS.GRAY;

/**
 * Display label for a field value, falling back to the option name.
 */
export const issueFieldValueLabel = (value) =>
  value?.value ?? value?.name ?? '';
