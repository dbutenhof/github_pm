// Assisted-by: Codex
// Generated-by: Cursor
// Assisted-by: Cline
/**
 * Flatten a nested issue forest into visible rows based on hierarchy expand state.
 */
export const flattenVisibleIssues = (forest, expandedNumbers) => {
  const rows = [];
  const walk = (nodes) => {
    for (const node of nodes || []) {
      rows.push(node);
      const children = node.children || [];
      if (children.length > 0 && expandedNumbers.has(node.number)) {
        walk(children);
      }
    }
  };
  walk(forest);
  return rows;
};

/**
 * Collect issue numbers in a subtree (including root).
 */
export const collectSubtreeNumbers = (issue) => {
  const numbers = new Set([issue.number]);
  const walk = (node) => {
    for (const child of node.children || []) {
      numbers.add(child.number);
      walk(child);
    }
  };
  walk(issue);
  return numbers;
};

/**
 * Keep the GitHub sub-issue total in sync with optimistic forest edits.
 *
 * The total counts all sub-issues, including closed ones and ones outside the
 * current milestone, so closing an issue must not decrement it.
 *
 * Generated-by: Cline
 */
const _subIssueTotal = (node) => {
  const total = Number(node?.sub_issues_summary?.total);
  return Number.isFinite(total) ? total : (node.children || []).length;
};

const _withSubIssueTotal = (node, total) => ({
  ...node,
  sub_issues_summary: {
    ...(node.sub_issues_summary || {}),
    total: Math.max(0, total),
  },
});

/**
 * Remove an issue (by number) from a forest; returns { forest, removed }.
 * The removed node retains its children subtree (used by DnD unlink/relink).
 *
 * `keepSubIssueTotal` skips parent total adjustments for close operations,
 * which remove the row but leave the sub-issue relationship intact.
 */
export const removeIssueFromForest = (
  forest,
  issueNumber,
  { keepSubIssueTotal = false } = {}
) => {
  let removed = null;
  const filterNodes = (nodes) => {
    const next = [];
    for (const node of nodes || []) {
      if (node.number === issueNumber) {
        removed = node;
        continue;
      }
      const originalChildren = node.children || [];
      const children = filterNodes(originalChildren);
      const removedChildren = originalChildren.length - children.length;
      let nextNode = {
        ...node,
        children,
        child_count: children.length,
      };
      if (!keepSubIssueTotal && removedChildren > 0) {
        nextNode = _withSubIssueTotal(
          nextNode,
          _subIssueTotal(node) - removedChildren
        );
      }
      next.push(nextNode);
    }
    return next;
  };
  return { forest: filterNodes(forest), removed };
};

/**
 * Remove a closed issue and promote its former children to forest roots.
 * Matches server build_issue_forest: closed parent is absent, children are
 * display roots with external_parent pointing at the closed parent.
 */
export const removeClosedIssueFromForest = (forest, issueNumber) => {
  const { forest: next, removed } = removeIssueFromForest(forest, issueNumber, {
    keepSubIssueTotal: true,
  });
  if (!removed) {
    return { forest: next, removed: null };
  }
  const milestone = removed.milestone;
  const externalParent = {
    number: removed.number,
    title: removed.title ?? null,
    milestone:
      milestone && typeof milestone === 'object'
        ? {
            number: milestone.number,
            title: milestone.title,
          }
        : null,
  };
  const promoted = (removed.children || []).map((child) => ({
    ...child,
    parent_number: null,
    external_parent: externalParent,
  }));
  return {
    forest: [...next, ...promoted],
    removed,
  };
};

/**
 * Insert issue as child of parentNumber, or as root if parentNumber is null.
 */
export const insertIssueInForest = (forest, issue, parentNumber) => {
  const node = {
    ...issue,
    parent_number: parentNumber,
    external_parent: null,
    children: issue.children || [],
    child_count: (issue.children || []).length,
  };

  if (parentNumber == null) {
    return [...forest, { ...node, hierarchy_depth: 0 }];
  }

  const mapNodes = (nodes, depth) =>
    (nodes || []).map((n) => {
      if (n.number === parentNumber) {
        const children = [
          ...(n.children || []),
          { ...node, hierarchy_depth: depth + 1 },
        ];
        return _withSubIssueTotal(
          {
            ...n,
            children,
            child_count: children.length,
          },
          _subIssueTotal(n) + 1
        );
      }
      return {
        ...n,
        children: mapNodes(n.children || [], depth + 1),
      };
    });

  return mapNodes(forest, 0);
};

/**
 * Recompute hierarchy_depth for every node from roots.
 */
export const reannotateDepths = (forest, depth = 0) =>
  (forest || []).map((node) => {
    const children = reannotateDepths(node.children || [], depth + 1);
    return {
      ...node,
      hierarchy_depth: depth,
      children,
      child_count: children.length,
    };
  });

// Generated-by: Codex
export const sortIssueForest = (items, sortOrder = []) => {
  const priorities = sortOrder.map((label) => label.trim());
  const bucket = (item) => {
    const labels = new Set(
      (item.labels || []).map((label) => label.name.toLowerCase())
    );
    const index = priorities.findIndex((label) => labels.has(label));
    return index < 0 ? priorities.length : index;
  };
  return (items || [])
    .map((item) => ({
      ...item,
      ...(item.children
        ? { children: sortIssueForest(item.children, sortOrder) }
        : {}),
    }))
    .sort((a, b) => bucket(a) - bucket(b) || a.number - b.number);
};
