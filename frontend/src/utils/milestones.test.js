// Generated-by: openai-code-assist
import { describe, expect, it } from 'vitest';
import { sortMilestones } from './milestones';

describe('milestone sorting', () => {
  it('sorts versions numerically and keeps non-version sections at the end', () => {
    const milestones = [
      { number: 9, title: 'v0.9.0' },
      { number: 0, title: 'none' },
      { number: 1, title: 'Backlog' },
      { number: 10, title: 'v0.10.0' },
      { number: 8, title: 'v0.8.1' },
    ];

    expect(
      sortMilestones(milestones).map((milestone) => milestone.title)
    ).toEqual(['v0.8.1', 'v0.9.0', 'v0.10.0', 'Backlog', 'none']);
  });
});
