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

const itemTableHeader = (
  <thead>
    <tr style={{ borderBottom: '2px solid #0066cc' }}>
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
          width: '2rem',
        }}
      />
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
        }}
      >
        Number
      </th>
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
        }}
      >
        Author
      </th>
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
        }}
      >
        PR
      </th>
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
        }}
      >
        Milestone
      </th>
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
        }}
      >
        Labels
      </th>
      <th
        style={{
          padding: '0.5rem',
          textAlign: 'left',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#6a6e73',
          textTransform: 'uppercase',
        }}
      >
        Title
      </th>
    </tr>
  </thead>
);

const MilestoneCard = ({
  milestone,
  sortOrder = [],
  issueMilestoneRefresh = { key: 0, milestoneNumbers: [] },
  onIssueMilestoneMoved,
  onIssueLabelsChanged,
}) => {
  const [isIssuesExpanded, setIsIssuesExpanded] = useState(false);
  const [isPrsExpanded, setIsPrsExpanded] = useState(false);
  const [issues, setIssues] = useState([]);
  const [pullRequests, setPullRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const prevMilestoneNumberRef = useRef(milestone.number);

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
    // Only refetch if sort order actually changed and issues are already loaded
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
    // Refresh even when collapsed so expanding later shows fresh data.
    if (!hasLoadedOnce) return;
    refetchIssues();
    // Bump `key` and `milestoneNumbers` update together; refetch only when key changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issueMilestoneRefresh.key]);

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
      const count = issues.length;
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

  const updateItemInList = (setter) => (updatedIssue) => {
    setter((prev) =>
      prev.map((item) => (item.id === updatedIssue.id ? updatedIssue : item))
    );
  };

  const renderItemTable = (items, onItemUpdate) => (
    <table
      style={{
        width: '100%',
        marginTop: '0.75rem',
        borderCollapse: 'collapse',
        border: '1px solid #d2d2d2',
      }}
    >
      {itemTableHeader}
      <tbody>
        {items.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onMilestoneChange={(detail) => {
              onIssueMilestoneMoved?.(detail);
            }}
            onLabelsChange={(detail) => {
              onIssueLabelsChanged?.(detail);
            }}
            onIssueUpdate={onItemUpdate}
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

          {!loading && !error && issues.length > 0 && (
            <>{renderItemTable(issues, updateItemInList(setIssues))}</>
          )}

          {!loading &&
            !error &&
            issues.length === 0 &&
            isIssuesExpanded &&
            hasLoadedOnce && (
              <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                No issues found for this milestone.
              </p>
            )}
        </ExpandableSection>

        {hasLoadedOnce && !error && pullRequests.length > 0 && (
          <div style={{ marginTop: '0.75rem' }}>
            <ExpandableSection
              toggleText={getPrsToggleText()}
              onToggle={() => setIsPrsExpanded(!isPrsExpanded)}
              isExpanded={isPrsExpanded}
            >
              {renderItemTable(pullRequests, updateItemInList(setPullRequests))}
            </ExpandableSection>
          </div>
        )}
      </CardBody>
    </Card>
  );
};

export default MilestoneCard;
