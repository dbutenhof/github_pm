// Generated-by: Cline
import { describe, it, expect } from 'vitest';
import { getIssueSubIssueCount, getIssueTypeKind } from './issueType';

describe('issueType utils', () => {
  it('takes the larger visible or summarized sub-issue count', () => {
    expect(getIssueSubIssueCount({ child_count: 2 })).toBe(2);
    expect(
      getIssueSubIssueCount({
        child_count: 1,
        sub_issues_summary: { total: 4 },
      })
    ).toBe(4);
    expect(getIssueSubIssueCount({ children: [{ number: 2 }] })).toBe(1);
  });

  it('treats issues with any sub-issues as epics', () => {
    expect(getIssueTypeKind({ child_count: 2, type: { name: 'Bug' } })).toBe(
      'epic'
    );
    expect(
      getIssueTypeKind({
        sub_issues_summary: { total: 1 },
        type: { name: 'Feature' },
      })
    ).toBe('epic');
  });

  it('maps the standard GitHub issue type names case-insensitively', () => {
    expect(getIssueTypeKind({ type: { name: 'Feature' } })).toBe('feature');
    expect(getIssueTypeKind({ type: { name: ' bug ' } })).toBe('bug');
    expect(getIssueTypeKind({ type: { name: 'TASK' } })).toBe('task');
  });

  it('falls back to custom and untyped issues', () => {
    expect(getIssueTypeKind({ type: { name: 'Research' } })).toBe('custom');
    expect(getIssueTypeKind({ type: { name: '' } })).toBe('untyped');
    expect(getIssueTypeKind({ type: null })).toBe('untyped');
    expect(getIssueTypeKind({})).toBe('untyped');
  });
});
