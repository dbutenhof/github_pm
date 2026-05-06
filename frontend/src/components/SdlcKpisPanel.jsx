// ai-generated: Cursor
import React, { useState, useCallback, useEffect } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  Spinner,
  Alert,
  ExpandableSection,
  Title,
} from '@patternfly/react-core';
import {
  fetchSdlcDelivery,
  fetchEscapedDefectRate,
  fetchBugBacklogDelta,
} from '../services/api';

/** Format a duration as whole days and hours only (no minutes/seconds). */
export const formatDaysAndHours = (sec) => {
  if (sec == null || Number.isNaN(sec)) {
    return '—';
  }
  if (sec <= 0) {
    return '0 h';
  }
  const days = Math.floor(sec / 86400);
  const hours = Math.floor((sec % 86400) / 3600);
  const parts = [];
  if (days > 0) {
    parts.push(`${days} d`);
  }
  if (hours > 0) {
    parts.push(`${hours} h`);
  }
  if (parts.length === 0) {
    return '< 1 h';
  }
  return parts.join(' ');
};

const formatMedianMap = (obj) =>
  Object.fromEntries(
    Object.entries(obj || {}).map(([k, v]) => [
      k,
      v != null ? formatDaysAndHours(v) : '—',
    ])
  );

const formatRate = (r) => {
  if (r == null || Number.isNaN(r)) {
    return '—';
  }
  return `${(r * 100).toFixed(1)}%`;
};

const BreakdownTable = ({ title, byType, bySize }) => (
  <div style={{ marginTop: '0.75rem' }}>
    <Title headingLevel="h5" size="md">
      {title}
    </Title>
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1rem',
        marginTop: '0.5rem',
      }}
    >
      <div>
        <strong style={{ fontSize: '0.875rem' }}>By PR type</strong>
        <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
          {Object.entries(byType || {}).map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <strong style={{ fontSize: '0.875rem' }}>By PR size</strong>
        <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem' }}>
          {Object.entries(bySize || {}).map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
        </ul>
      </div>
    </div>
  </div>
);

const SdlcKpisPanel = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [delivery, setDelivery] = useState(null);
  const [escaped, setEscaped] = useState(null);
  const [backlog, setBacklog] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      fetchSdlcDelivery(7),
      fetchEscapedDefectRate(),
      fetchBugBacklogDelta(7),
    ])
      .then(([d, e, b]) => {
        setDelivery(d);
        setEscaped(e);
        setBacklog(b);
        setLoading(false);
        setHasLoadedOnce(true);
      })
      .catch((err) => {
        setError(err.message || String(err));
        setLoading(false);
        setHasLoadedOnce(true);
      });
  }, []);

  const handleToggle = (_event, expanded) => setIsExpanded(expanded);

  useEffect(() => {
    if (isExpanded && !hasLoadedOnce && !loading) {
      load();
    }
  }, [isExpanded, hasLoadedOnce, loading, load]);

  const tp = delivery?.merged_pr_throughput;
  const cycle = delivery?.median_pr_cycle_time;
  const review = delivery?.median_time_to_first_review;

  return (
    <Card>
      <CardHeader>
        <CardTitle>SDLC KPIs</CardTitle>
      </CardHeader>
      <CardBody>
        <ExpandableSection
          toggleText={
            isExpanded ? 'Hide SDLC metrics' : 'Show SDLC metrics (delivery & quality)'
          }
          onToggle={handleToggle}
          isExpanded={isExpanded}
        >
          {loading && (
            <div style={{ textAlign: 'center', padding: '1.5rem' }}>
              <Spinner size="lg" />
            </div>
          )}
          {error && (
            <Alert variant="danger" title="Error loading SDLC metrics">
              {error}
            </Alert>
          )}
          {!loading && !error && delivery && escaped && backlog && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
              }}
            >
              <section>
                <Title headingLevel="h4" size="lg">
                  Delivery (last {delivery.window_days} days)
                </Title>
                <p style={{ color: '#6a6e73', fontSize: '0.875rem' }}>
                  As of {new Date(delivery.as_of).toLocaleString()}
                </p>

                <Title headingLevel="h5" size="md" style={{ marginTop: '0.75rem' }}>
                  1. Merged PR throughput
                </Title>
                <p>
                  <strong>{tp?.total ?? 0}</strong> merged PRs
                </p>
                <BreakdownTable
                  title="Breakdown"
                  byType={tp?.by_pr_type}
                  bySize={tp?.by_pr_size}
                />

                <Title headingLevel="h5" size="md" style={{ marginTop: '1rem' }}>
                  2. Median PR cycle time (open → merge)
                </Title>
                <p>
                  Overall:{' '}
                  <strong>
                    {formatDaysAndHours(cycle?.median_seconds)}
                  </strong>{' '}
                  ({cycle?.pr_count ?? 0} PRs)
                </p>
                <BreakdownTable
                  title="Median by category (days & hours)"
                  byType={formatMedianMap(cycle?.by_pr_type)}
                  bySize={formatMedianMap(cycle?.by_pr_size)}
                />

                <Title headingLevel="h5" size="md" style={{ marginTop: '1rem' }}>
                  3. Median time to first human review
                </Title>
                <p style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
                  PRs opened in the window: {review?.eligible_pr_count ?? 0}; with
                  a human review: {review?.included_pr_count ?? 0}
                </p>
                <p>
                  Overall:{' '}
                  <strong>
                    {formatDaysAndHours(review?.median_seconds)}
                  </strong>
                </p>
                <BreakdownTable
                  title="Median by category (days & hours)"
                  byType={formatMedianMap(review?.by_pr_type)}
                  bySize={formatMedianMap(review?.by_pr_size)}
                />
              </section>

              <section>
                <Title headingLevel="h4" size="lg">
                  Quality
                </Title>

                <Title headingLevel="h5" size="md" style={{ marginTop: '0.5rem' }}>
                  4. Escaped defect rate (per release milestone)
                </Title>
                <p style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
                  Issues with the configured escape label and a semver milestone count toward
                  the <strong>previous</strong> milestone in global version order. Rate is
                  escapes ÷ (feature + bug-fix + docs PRs merged in that milestone; bot PRs
                  excluded from denominators). Same milestone window:{' '}
                  <strong>lowest open</strong> release line plus two previous minor lines
                  (latest closed per line). Sorted by version. As of{' '}
                  {new Date(escaped.as_of).toLocaleString()}.
                </p>
                <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem' }}>
                  {(escaped.releases || []).map((row) => (
                    <li key={`${row.release}-${row.is_next_open ? 'next' : 'closed'}`}>
                      <strong>{row.release}</strong>
                      {row.is_next_open ? (
                        <span style={{ color: '#6a6e73' }}>
                          {' '}
                          (next open / pre-release)
                        </span>
                      ) : null}
                      : {formatRate(row.rate)} ({row.escape_issues ?? 0} escape(s); features{' '}
                      {row.feature_prs}, bugs {row.bug_fix_prs}, docs {row.docs_prs ?? 0})
                    </li>
                  ))}
                </ul>

                <Title headingLevel="h5" size="md" style={{ marginTop: '1rem' }}>
                  5. Open bug backlog growth (last {backlog.window_days} days)
                </Title>
                <p>
                  Opened: <strong>{backlog.bugs_opened}</strong>, closed:{' '}
                  <strong>{backlog.bugs_closed}</strong>, net:{' '}
                  <strong>{backlog.net}</strong>
                </p>
                <p style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
                  As of {new Date(backlog.as_of).toLocaleString()}
                </p>
              </section>
            </div>
          )}
        </ExpandableSection>
      </CardBody>
    </Card>
  );
};

export default SdlcKpisPanel;
