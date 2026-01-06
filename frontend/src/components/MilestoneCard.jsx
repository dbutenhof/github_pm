// ai-generated: Cursor
import React, { useState, useEffect, useRef } from 'react';
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

const MilestoneCard = ({ milestone, sortOrder = [] }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const prevMilestoneNumberRef = useRef(milestone.number);

  // Reset loaded state when milestone changes
  useEffect(() => {
    if (prevMilestoneNumberRef.current !== milestone.number) {
      prevMilestoneNumberRef.current = milestone.number;
      setHasLoadedOnce(false);
      setIssues([]);
      setError(null);
      setLoading(false);
    }
  }, [milestone.number]);

  useEffect(() => {
    if (isExpanded && !hasLoadedOnce && !loading) {
      setLoading(true);
      setError(null);
      fetchIssues(milestone.number, sortOrder)
        .then((data) => {
          setIssues(data);
          setLoading(false);
          setHasLoadedOnce(true);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
          setHasLoadedOnce(true);
        });
    }
  }, [isExpanded, milestone.number, hasLoadedOnce, loading, sortOrder]);

  // Re-fetch issues when sort order changes (if already loaded)
  const prevSortOrderRef = useRef(sortOrder);
  useEffect(() => {
    // Only refetch if sort order actually changed and issues are already loaded
    const sortOrderChanged =
      JSON.stringify(prevSortOrderRef.current) !== JSON.stringify(sortOrder);
    if (isExpanded && hasLoadedOnce && !loading && sortOrderChanged) {
      prevSortOrderRef.current = sortOrder;
      setLoading(true);
      setError(null);
      fetchIssues(milestone.number, sortOrder)
        .then((data) => {
          setIssues(data);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    } else {
      prevSortOrderRef.current = sortOrder;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortOrder]);

  const formatDueDate = (dueOn) => {
    if (!dueOn) return 'No due date';
    const date = new Date(dueOn);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getToggleText = () => {
    const baseText = isExpanded ? 'Hide' : 'Show';

    if (hasLoadedOnce) {
      const count = issues.length;
      const issueText = count === 1 ? 'issue' : 'issues';
      return `${baseText} ${count} ${issueText}`;
    }

    return `${baseText} Issues`;
  };

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
          toggleText={getToggleText()}
          onToggle={() => setIsExpanded(!isExpanded)}
          isExpanded={isExpanded}
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
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                marginTop: '0.75rem',
              }}
            >
              {issues.map((issue) => (
                <IssueCard
                  key={issue.id}
                  issue={issue}
                  onMilestoneChange={() => {
                    // Refresh issues when milestone changes
                    if (isExpanded) {
                      setLoading(true);
                      setError(null);
                      fetchIssues(milestone.number, sortOrder)
                        .then((data) => {
                          setIssues(data);
                          setLoading(false);
                        })
                        .catch((err) => {
                          setError(err.message);
                          setLoading(false);
                        });
                    }
                  }}
                />
              ))}
            </div>
          )}

          {!loading &&
            !error &&
            issues.length === 0 &&
            isExpanded &&
            hasLoadedOnce && (
              <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                No issues found for this milestone.
              </p>
            )}
        </ExpandableSection>
      </CardBody>
    </Card>
  );
};

export default MilestoneCard;
