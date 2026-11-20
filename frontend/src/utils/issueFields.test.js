// Generated-by: Cline
import { describe, it, expect } from 'vitest';
import {
  PLANNING_ISSUE_FIELD_NAMES,
  findIssueFieldValue,
  findPlanningIssueFields,
  issueFieldOptionColor,
  issueFieldValueLabel,
} from './issueFields';

const priority = {
  id: 'F1',
  name: 'Priority',
  data_type: 'SINGLE_SELECT',
  options: [
    { id: 'O1', name: 'High', color: 'RED', priority: 1 },
    { id: 'O2', name: 'Low', color: 'GREEN', priority: 2 },
  ],
};
const effort = {
  id: 'F2',
  name: 'Effort',
  data_type: 'SINGLE_SELECT',
  options: [{ id: 'O3', name: 'Medium', color: 'YELLOW', priority: 1 }],
};

describe('issueFields', () => {
  it('selects Priority and Effort in the configured column order', () => {
    expect(PLANNING_ISSUE_FIELD_NAMES).toEqual(['Priority', 'Effort']);
    expect(
      findPlanningIssueFields([
        effort,
        { id: 'F3', name: 'Start date', data_type: 'DATE' },
        priority,
      ])
    ).toEqual([priority, effort]);
  });

  it('matches the field name case-insensitively', () => {
    expect(
      findPlanningIssueFields([{ ...priority, name: 'priority' }])[0].id
    ).toBe('F1');
  });

  it('returns no columns when a field is unavailable', () => {
    expect(findPlanningIssueFields([{ ...effort }])).toEqual([effort]);
    expect(findPlanningIssueFields([])).toEqual([]);
    expect(findPlanningIssueFields(undefined)).toEqual([]);
  });

  it('ignores non-single-select fields with matching names', () => {
    expect(
      findPlanningIssueFields([{ ...priority, data_type: 'TEXT' }])
    ).toEqual([]);
  });

  it('finds an issue value by field id or name', () => {
    const values = [
      {
        field_id: 'F1',
        field_name: 'Priority',
        value: 'High',
        option_id: 'O1',
        color: 'RED',
      },
    ];
    expect(findIssueFieldValue(values, priority)).toMatchObject({
      option_id: 'O1',
    });
    expect(
      findIssueFieldValue(values, { id: 'other', name: 'Priority' })
    ).toMatchObject({ option_id: 'O1' });
    expect(findIssueFieldValue(values, effort)).toBeNull();
    expect(findIssueFieldValue(undefined, priority)).toBeNull();
  });

  it('maps option colors and value labels', () => {
    expect(issueFieldOptionColor('PINK')).toBe('#bf3989');
    expect(issueFieldOptionColor('unknown')).toBe('#6e7781');
    expect(issueFieldOptionColor(undefined)).toBe('#6e7781');
    expect(issueFieldValueLabel({ value: 'High', name: 'High' })).toBe('High');
    expect(issueFieldValueLabel({ name: 'Low' })).toBe('Low');
    expect(issueFieldValueLabel(null)).toBe('');
  });
});
