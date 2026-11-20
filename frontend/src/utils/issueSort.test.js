// Generated-by: Cline
import { describe, it, expect } from 'vitest';
import {
  planningFieldSortKey,
  sortIssueForestByLabels,
  sortIssueForestBySpec,
} from './issueSort';

const issue = (number, overrides = {}) => ({
  number,
  title: `Issue ${number}`,
  user: { login: `user${number}` },
  labels: [],
  children: [],
  ...overrides,
});

const priorityField = {
  id: 'priority',
  name: 'Priority',
  options: [
    { id: 'urgent', name: 'Urgent', priority: 1 },
    { id: 'high', name: 'High', priority: 2 },
    { id: 'medium', name: 'Medium', priority: 3 },
    { id: 'low', name: 'Low', priority: 4 },
  ],
};

const effortField = {
  id: 'effort',
  name: 'Effort',
  options: [
    { id: 'high', name: 'High', priority: 1 },
    { id: 'medium', name: 'Medium', priority: 2 },
    { id: 'low', name: 'Low', priority: 3 },
  ],
};

const fieldValue = (name, optionId) => ({
  field_name: name,
  option_id: optionId,
  value: optionId,
});

describe('issueSort utils', () => {
  it('sorts siblings recursively by number in either direction', () => {
    const forest = [issue(2, { children: [issue(5), issue(3)] }), issue(1)];
    const ascending = sortIssueForestBySpec(forest, {
      mode: 'column',
      key: 'number',
      direction: 'asc',
    });
    expect(ascending.map((item) => item.number)).toEqual([1, 2]);
    expect(ascending[1].children.map((item) => item.number)).toEqual([3, 5]);

    const descending = sortIssueForestBySpec(forest, {
      mode: 'column',
      key: 'number',
      direction: 'desc',
    });
    expect(descending.map((item) => item.number)).toEqual([2, 1]);
    expect(descending[0].children.map((item) => item.number)).toEqual([5, 3]);
    expect(forest[0].children.map((item) => item.number)).toEqual([5, 3]);
  });

  it('sorts type labels alphabetically and keeps untyped issues last', () => {
    const forest = [
      issue(6),
      issue(1, { type: { name: 'Task' } }),
      issue(2, { type: { name: 'Bug' } }),
      issue(3, { type: { name: 'Feature' } }),
      issue(4, { type: { name: 'Research' } }),
      issue(5, { child_count: 1, type: { name: 'Bug' } }),
    ];
    const ascending = sortIssueForestBySpec(forest, {
      mode: 'column',
      key: 'type',
      direction: 'asc',
    });
    expect(
      ascending.map((item) =>
        item.child_count ? 'Epic' : item.type?.name || ''
      )
    ).toEqual(['Bug', 'Epic', 'Feature', 'Research', 'Task', '']);

    const descending = sortIssueForestBySpec(forest, {
      mode: 'column',
      key: 'type',
      direction: 'desc',
    });
    expect(
      descending.map((item) =>
        item.child_count ? 'Epic' : item.type?.name || ''
      )
    ).toEqual(['Task', 'Research', 'Feature', 'Epic', 'Bug', '']);
  });

  it('sorts author and title naturally with blanks last', () => {
    const forest = [
      issue(1, { user: null }),
      issue(2, { user: { login: 'Zed' }, title: 'issue 10' }),
      issue(3, { user: { login: 'alice' }, title: 'Issue 2' }),
    ];
    expect(
      sortIssueForestBySpec(forest, {
        mode: 'column',
        key: 'author',
        direction: 'asc',
      }).map((item) => item.user?.login || '')
    ).toEqual(['alice', 'Zed', '']);

    expect(
      sortIssueForestBySpec(forest, {
        mode: 'column',
        key: 'title',
        direction: 'asc',
      }).map((item) => item.title)
    ).toEqual(['Issue 1', 'Issue 2', 'issue 10']);
  });

  it('sorts Priority and Effort semantically from low to high', () => {
    const forest = [
      issue(1, {
        issue_field_values: [fieldValue('Priority', 'low')],
      }),
      issue(2, {
        issue_field_values: [fieldValue('Priority', 'urgent')],
      }),
      issue(3, {
        issue_field_values: [fieldValue('Priority', 'medium')],
      }),
      issue(4),
      issue(5, {
        issue_field_values: [fieldValue('Priority', 'high')],
      }),
    ];
    expect(
      sortIssueForestBySpec(forest, {
        mode: 'column',
        key: planningFieldSortKey(priorityField),
        direction: 'asc',
        fields: [priorityField],
      }).map((item) => item.number)
    ).toEqual([1, 3, 5, 2, 4]);

    expect(
      sortIssueForestBySpec(forest, {
        mode: 'column',
        key: planningFieldSortKey(priorityField),
        direction: 'desc',
        fields: [priorityField],
      }).map((item) => item.number)
    ).toEqual([2, 5, 3, 1, 4]);

    const effortForest = [
      issue(1, { issue_field_values: [fieldValue('Effort', 'high')] }),
      issue(2, { issue_field_values: [fieldValue('Effort', 'low')] }),
      issue(3),
      issue(4, { issue_field_values: [fieldValue('Effort', 'medium')] }),
    ];
    expect(
      sortIssueForestBySpec(effortForest, {
        mode: 'column',
        key: planningFieldSortKey(effortField),
        direction: 'asc',
        fields: [effortField],
      }).map((item) => item.number)
    ).toEqual([2, 4, 1, 3]);
  });

  it('sorts by label order and keeps unlisted labels last', () => {
    const forest = [
      issue(3),
      issue(1, { labels: [{ name: 'Feature' }] }),
      issue(2, { labels: [{ name: 'bug' }, { name: 'other' }] }),
    ];
    const ordered = sortIssueForestByLabels(forest, ['BUG', 'feature']);
    expect(ordered.map((item) => item.number)).toEqual([2, 1, 3]);
  });

  it('uses number as a stable tie-break', () => {
    const forest = [
      issue(9, { title: 'Same', user: { login: 'same' } }),
      issue(4, { title: 'Same', user: { login: 'same' } }),
    ];
    expect(
      sortIssueForestBySpec(forest, {
        mode: 'column',
        key: 'title',
        direction: 'desc',
      }).map((item) => item.number)
    ).toEqual([4, 9]);
  });
});
