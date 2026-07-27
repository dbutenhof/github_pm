// Generated-by: Cursor
import { describe, it, expect } from 'vitest';
import {
  flattenVisibleIssues,
  collectSubtreeNumbers,
  removeIssueFromForest,
  removeClosedIssueFromForest,
  insertIssueInForest,
  reannotateDepths,
} from './issueHierarchy';

describe('issueHierarchy utils', () => {
  const forest = [
    {
      number: 1,
      id: 1,
      children: [
        {
          number: 2,
          id: 2,
          children: [{ number: 3, id: 3, children: [] }],
          child_count: 1,
        },
      ],
      child_count: 1,
    },
    { number: 4, id: 4, children: [], child_count: 0 },
  ];

  it('flattens only expanded branches', () => {
    expect(
      flattenVisibleIssues(forest, new Set()).map((i) => i.number)
    ).toEqual([1, 4]);
    expect(
      flattenVisibleIssues(forest, new Set([1])).map((i) => i.number)
    ).toEqual([1, 2, 4]);
    expect(
      flattenVisibleIssues(forest, new Set([1, 2])).map((i) => i.number)
    ).toEqual([1, 2, 3, 4]);
  });

  it('collects subtree numbers', () => {
    expect([...collectSubtreeNumbers(forest[0])].sort()).toEqual([1, 2, 3]);
  });

  it('removes an issue from the forest', () => {
    const { forest: next, removed } = removeIssueFromForest(forest, 2);
    expect(removed.number).toBe(2);
    expect(removed.children.map((c) => c.number)).toEqual([3]);
    expect(next[0].children).toEqual([]);
    expect(next[0].child_count).toBe(0);
  });

  it('promotes children to roots when removing a closed issue', () => {
    const nested = [
      {
        number: 1,
        id: 1,
        title: 'Epic',
        milestone: { number: 6, title: 'v0.6.0' },
        children: [
          {
            number: 2,
            id: 2,
            title: 'Parent',
            parent_number: 1,
            children: [
              {
                number: 3,
                id: 3,
                title: 'Child',
                parent_number: 2,
                children: [],
                child_count: 0,
              },
            ],
            child_count: 1,
          },
        ],
        child_count: 1,
      },
    ];
    const { forest: next, removed } = removeClosedIssueFromForest(nested, 2);
    expect(removed.number).toBe(2);
    expect(next.map((n) => n.number)).toEqual([1, 3]);
    expect(next[0].children).toEqual([]);
    expect(next[1].parent_number).toBeNull();
    expect(next[1].external_parent).toEqual({
      number: 2,
      title: 'Parent',
      milestone: null,
    });
    const annotated = reannotateDepths(next);
    expect(annotated[1].hierarchy_depth).toBe(0);
  });

  it('promotes nested grandchildren when closing a root', () => {
    const { forest: next } = removeClosedIssueFromForest(forest, 1);
    expect(next.map((n) => n.number)).toEqual([4, 2]);
    expect(next[1].children.map((c) => c.number)).toEqual([3]);
    expect(next[1].parent_number).toBeNull();
    expect(next[1].external_parent.number).toBe(1);
  });

  it('inserts under a parent and reannotates depths', () => {
    const inserted = insertIssueInForest(
      [{ number: 1, id: 1, children: [], child_count: 0 }],
      { number: 9, id: 9, children: [] },
      1
    );
    const annotated = reannotateDepths(inserted);
    expect(annotated[0].hierarchy_depth).toBe(0);
    expect(annotated[0].children[0].number).toBe(9);
    expect(annotated[0].children[0].hierarchy_depth).toBe(1);
  });
});
