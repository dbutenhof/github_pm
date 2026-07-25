// Generated-by: Cursor
// Assisted-by: Cursor
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  Spinner,
  Alert,
  ExpandableSection,
} from '@patternfly/react-core';
import { fetchIssues } from '../services/api';
import IssueCard from './IssueCard';
import { usePlanningDnD } from './PlanningDnDContext';
import {
  flattenVisibleIssues,
  collectSubtreeNumbers,
  removeIssueFromForest,
  insertIssueInForest,
  reannotateDepths,
} from '../utils/issueHierarchy';

const thStyle = {
  padding: '0.5rem',
  textAlign: 'left',
  fontSize: '0.75rem',
  fontWeight: '600',
  color: '#6a6e73',
  textTransform: 'uppercase',
};

const itemTableHeader = (includeType) => (
  <thead>
    <tr style={{ borderBottom: '2px solid #0066cc' }}>
      <th style={{ ...thStyle, width: '2rem' }} />
      <th style={thStyle}>Number</th>
      {includeType && <th style={thStyle}>Type</th>}
      <th style={thStyle}>Author</th>
      <th style={thStyle}>PR</th>
      <th style={thStyle}>Milestone</th>
      <th style={thStyle}>Labels</th>
      <th style={thStyle}>Title</th>
    </tr>
  </thead>
);

const MilestoneCard = ({
  milestone,
  sortOrder = [],
  issueMilestoneRefresh = { key: 0, milestoneNumbers: [] },
  onIssueMilestoneMoved,
  onIssueLabelsChanged,
  hierarchyAction,
}) => {
  const [isIssuesExpanded, setIsIssuesExpanded] = useState(false);
  const [isPrsExpanded, setIsPrsExpanded] = useState(false);
  const [issues, setIssues] = useState([]);
  const [pullRequests, setPullRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [expandedHierarchy, setExpandedHierarchy] = useState(() => new Set());
  const prevMilestoneNumberRef = useRef(milestone.number);
  const dnd = usePlanningDnD();

  const applyFetchedData = useCallback((data) => {
    setIssues(data.issues || []);
    setPullRequests(data.pull_requests || []);
  }, []);

  const refetchIssues = useCallback(() => {
    setLoading(true);
    setError(null);
    return fetchIssues(milestone.number, sortOrder)
      .then((data) => {
        applyFetchedData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [milestone.number, sortOrder, applyFetchedData]);

  // Reset loaded state when milestone changes
  useEffect(() => {
    if (prevMilestoneNumberRef.current !== milestone.number) {
      prevMilestoneNumberRef.current = milestone.number;
      setHasLoadedOnce(false);
      setIssues([]);
      setPullRequests([]);
      setError(null);
      setLoading(false);
      setIsPrsExpanded(false);
      setExpandedHierarchy(new Set());
    }
  }, [milestone.number]);

  useEffect(() => {
    if (isIssuesExpanded && !hasLoadedOnce && !loading) {
      setLoading(true);
      setError(null);
      fetchIssues(milestone.number, sortOrder)
        .then((data) => {
          applyFetchedData(data);
          setLoading(false);
          setHasLoadedOnce(true);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
          setHasLoadedOnce(true);
        });
    }
  }, [
    isIssuesExpanded,
    milestone.number,
    hasLoadedOnce,
    loading,
    sortOrder,
    applyFetchedData,
  ]);

  // Re-fetch issues when sort order changes (if already loaded)
  const prevSortOrderRef = useRef(sortOrder);
  useEffect(() => {
    const sortOrderChanged =
      JSON.stringify(prevSortOrderRef.current) !== JSON.stringify(sortOrder);
    if (isIssuesExpanded && hasLoadedOnce && !loading && sortOrderChanged) {
      prevSortOrderRef.current = sortOrder;
      refetchIssues();
    } else {
      prevSortOrderRef.current = sortOrder;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortOrder]);

  useEffect(() => {
    const { key, milestoneNumbers } = issueMilestoneRefresh;
    if (key === 0) return;
    if (!milestoneNumbers.includes(milestone.number)) return;
    if (!hasLoadedOnce) return;
    refetchIssues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issueMilestoneRefresh.key]);

  // Apply optimistic hierarchy mutations from Planning DnD / adopt.
  useEffect(() => {
    if (!hierarchyAction || !hasLoadedOnce) return;
    const {
      type,
      issueNumber,
      parentNumber,
      sourceMilestoneNumber,
      targetMilestoneNumber,
      issueSnapshot,
    } = hierarchyAction;

    if (type === 'unlink') {
      if (sourceMilestoneNumber !== milestone.number) return;
      setIssues((prev) => {
        const { forest, removed } = removeIssueFromForest(prev, issueNumber);
        if (!removed) return prev;
        const asEpic = {
          ...removed,
          parent_number: null,
          external_parent: null,
          hierarchy_depth: 0,
        };
        return reannotateDepths([...forest, asEpic]);
      });
      return;
    }

    if (type === 'relink') {
      const touchesSource = sourceMilestoneNumber === milestone.number;
      const touchesTarget = targetMilestoneNumber === milestone.number;
      if (!touchesSource && !touchesTarget) return;

      setIssues((prev) => {
        let forest = prev;
        let removed = issueSnapshot || null;
        if (touchesSource) {
          const result = removeIssueFromForest(forest, issueNumber);
          forest = result.forest;
          removed = result.removed || removed;
        }
        if (touchesTarget && removed) {
          forest = insertIssueInForest(forest, removed, parentNumber);
          forest = reannotateDepths(forest);
          setExpandedHierarchy((exp) => new Set(exp).add(parentNumber));
        }
        return forest;
      });
    }
  }, [hierarchyAction, hasLoadedOnce, milestone.number]);

  const formatDueDate = (dueOn) => {
    if (!dueOn) return 'No due date';
    const date = new Date(dueOn);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getIssuesToggleText = () => {
    const baseText = isIssuesExpanded ? 'Hide' : 'Show';

    if (hasLoadedOnce) {
      const countVisible = (nodes) =>
        (nodes || []).reduce((sum, n) => sum + 1 + countVisible(n.children), 0);
      const count = countVisible(issues);
      const issueText = count === 1 ? 'issue' : 'issues';
      return `${baseText} ${count} ${issueText}`;
    }

    return `${baseText} Issues`;
  };

  const getPrsToggleText = () => {
    const baseText = isPrsExpanded ? 'Hide' : 'Show';
    const count = pullRequests.length;
    const prText = count === 1 ? 'PR' : 'PRs';
    return `${baseText} ${count} ${prText}`;
  };

  const updateItemInForest = (setter) => (updatedIssue) => {
    setter((prev) => {
      const mapNodes = (nodes) =>
        (nodes || []).map((item) => {
          if (item.id === updatedIssue.id) {
            return {
              ...item,
              ...updatedIssue,
              children: updatedIssue.children ?? item.children,
            };
          }
          return {
            ...item,
            children: mapNodes(item.children),
          };
        });
      return mapNodes(prev);
    });
  };

  const toggleHierarchy = (issueNumber) => {
    setExpandedHierarchy((prev) => {
      const next = new Set(prev);
      if (next.has(issueNumber)) next.delete(issueNumber);
      else next.add(issueNumber);
      return next;
    });
  };

  const renderIssueTable = () => {
    const visible = flattenVisibleIssues(issues, expandedHierarchy);
    return (
      <table
        style={{
          width: '100%',
          marginTop: '0.75rem',
          borderCollapse: 'collapse',
          border: '1px solid #d2d2d2',
        }}
      >
        {itemTableHeader(true)}
        <tbody>
          {visible.map((issue) => (
            <IssueCard
              key={issue.id}
              issue={issue}
              enableHierarchy
              columnCount={8}
              isHierarchyExpanded={expandedHierarchy.has(issue.number)}
              onToggleHierarchy={() => toggleHierarchy(issue.number)}
              isDropTarget={
                dnd?.hoverParent?.issue?.number === issue.number &&
                dnd?.hoverParent?.milestoneNumber === milestone.number
              }
              isDragging={dnd?.dragged?.issue?.number === issue.number}
              onDragStartIssue={(e) => {
                dnd?.beginDrag(e, {
                  issue,
                  sourceMilestoneNumber: milestone.number,
                  descendantNumbers: collectSubtreeNumbers(issue),
                });
              }}
              onDragOverIssue={(e) => {
                e.preventDefault();
                dnd?.pointerOverParent(issue, milestone.number);
              }}
              onDragEndIssue={() => {
                dnd?.finishDrag();
              }}
              onMilestoneChange={(detail) => {
                onIssueMilestoneMoved?.(detail);
              }}
              onLabelsChange={(detail) => {
                onIssueLabelsChanged?.(detail);
              }}
              onIssueUpdate={updateItemInForest(setIssues)}
              onAdoptParentMilestone={(detail) => {
                onIssueMilestoneMoved?.(detail);
              }}
            />
          ))}
        </tbody>
      </table>
    );
  };

  const renderPrTable = () => (
    <table
      style={{
        width: '100%',
        marginTop: '0.75rem',
        borderCollapse: 'collapse',
        border: '1px solid #d2d2d2',
      }}
    >
      {itemTableHeader(false)}
      <tbody>
        {pullRequests.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            enableHierarchy={false}
            columnCount={7}
            onMilestoneChange={(detail) => {
              onIssueMilestoneMoved?.(detail);
            }}
            onLabelsChange={(detail) => {
              onIssueLabelsChanged?.(detail);
            }}
            onIssueUpdate={updateItemInForest(setPullRequests)}
          />
        ))}
      </tbody>
    </table>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{milestone.title}</CardTitle>
      </CardHeader>
      <CardBody>
        <div style={{ marginBottom: '1rem' }}>
          {milestone.description && (
            <p style={{ marginBottom: '0.5rem' }}>{milestone.description}</p>
          )}
          <p style={{ color: '#6a6e73', fontSize: '0.875rem' }}>
            Due: {formatDueDate(milestone.due_on)}
          </p>
        </div>

        <ExpandableSection
          toggleText={getIssuesToggleText()}
          onToggle={() => setIsIssuesExpanded(!isIssuesExpanded)}
          isExpanded={isIssuesExpanded}
        >
          {loading && (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <Spinner size="lg" />
            </div>
          )}

          {error && (
            <Alert variant="danger" title="Error loading issues">
              {error}
            </Alert>
          )}

          {!loading && !error && issues.length === 0 && hasLoadedOnce && (
            <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
              No issues found for this milestone.
            </p>
          )}

          {!loading && !error && issues.length > 0 && renderIssueTable()}
        </ExpandableSection>

        {hasLoadedOnce && pullRequests.length > 0 && (
          <ExpandableSection
            toggleText={getPrsToggleText()}
            onToggle={() => setIsPrsExpanded(!isPrsExpanded)}
            isExpanded={isPrsExpanded}
            style={{ marginTop: '0.75rem' }}
          >
            {renderPrTable()}
          </ExpandableSection>
        )}
      </CardBody>
    </Card>
  );
};

export default MilestoneCard;
