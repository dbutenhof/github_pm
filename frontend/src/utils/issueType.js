// Generated-by: Cline
/**
 * Maximum of the locally visible child count and GitHub's sub-issue total.
 * GitHub's total also includes closed sub-issues and sub-issues that live in
 * other milestones, so it is the authoritative value when present.
 */
export const getIssueSubIssueCount = (issue) => {
  const children = Array.isArray(issue?.children) ? issue.children : [];
  const childCount = Number(issue?.child_count ?? children.length) || 0;
  const summaryTotal = Number(issue?.sub_issues_summary?.total) || 0;
  return Math.max(childCount, summaryTotal);
};

/**
 * Return the display kind for an issue's Type column.
 *
 * An issue with any sub-issue is an Epic; otherwise the GitHub issue type
 * determines the icon. Custom type names fall back to a generic icon, and
 * issues without a type are marked as untyped.
 */
export const getIssueTypeKind = (issue) => {
  if (getIssueSubIssueCount(issue) > 0) return 'epic';

  const name = String(issue?.type?.name || '')
    .trim()
    .toLowerCase();
  if (name === 'bug' || name === 'feature' || name === 'task') return name;
  return name ? 'custom' : 'untyped';
};
