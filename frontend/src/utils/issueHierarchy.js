// Generated-by: Cursor
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
 * Remove an issue (by number) from a forest; returns { forest, removed }.
 */
export const removeIssueFromForest = (forest, issueNumber) => {
  let removed = null;
  const filterNodes = (nodes) => {
    const next = [];
    for (const node of nodes || []) {
      if (node.number === issueNumber) {
        removed = node;
        continue;
      }
      const children = filterNodes(node.children || []);
      next.push({
        ...node,
        children,
        child_count: children.length,
      });
    }
    return next;
  };
  return { forest: filterNodes(forest), removed };
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
        return {
          ...n,
          children,
          child_count: children.length,
        };
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
