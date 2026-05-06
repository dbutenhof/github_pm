// ai-generated: Cursor
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardTitle,
  FormGroup,
  Spinner,
  TextContent,
  TextInput,
  Title,
} from '@patternfly/react-core';
import { OutlinedCopyIcon } from '@patternfly/react-icons';
import { fetchProjectStatusReport } from '../services/api';
import { copyStatusSectionToClipboard } from '../utils/clipboard';
import { formatDate, getLocalDateISOString } from '../utils/dateUtils';

const emptyListMessage = 'None in this period.';

const StatusSection = ({ heading, items }) => {
  const hasItems = items && items.length > 0;
  const copyLines = () => {
    if (!hasItems) {
      return;
    }
    void copyStatusSectionToClipboard(items);
  };

  return (
  <Card isCompact style={{ marginTop: '1rem' }}>
    <CardTitle>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
        <Button
          type="button"
          variant="plain"
          aria-label={`Copy ${heading} to clipboard`}
          title="Copy for reports: rich paste keeps # as a link to GitHub; plain text uses Markdown [#n](url) before the title"
          icon={<OutlinedCopyIcon />}
          onClick={copyLines}
          isDisabled={!hasItems}
        />
        <Title headingLevel="h3" size="lg">
          {heading}
        </Title>
      </div>
    </CardTitle>
    <CardBody>
      {!items || items.length === 0 ? (
        <TextContent>{emptyListMessage}</TextContent>
      ) : (
        <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
          {items.map((row) => (
            <li key={`${heading}-${row.number}`} style={{ marginBottom: '0.35rem' }}>
              <a href={row.html_url} target="_blank" rel="noopener noreferrer">
                #{row.number}
              </a>
              <span style={{ marginLeft: '0.35rem' }}>{row.title}</span>
            </li>
          ))}
        </ul>
      )}
    </CardBody>
  </Card>
  );
};

const ProjectStatusPanel = () => {
  const [endDate, setEndDate] = useState(() => getLocalDateISOString());
  const [draftEndDate, setDraftEndDate] = useState(() => getLocalDateISOString());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);

  const load = useCallback(async (iso) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjectStatusReport(iso);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e?.message || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(endDate);
  }, [endDate, load]);

  const onApplyDate = () => {
    setEndDate(draftEndDate);
  };

  const windowLabel =
    report?.start_date && report?.end_date
      ? `${formatDate(`${report.start_date}T12:00:00Z`)} — ${formatDate(`${report.end_date}T12:00:00Z`)}`
      : '';

  return (
    <div style={{ maxWidth: '960px' }}>
      <TextContent>
        <Title headingLevel="h2" size="xl">
          Project status
        </Title>
        <p style={{ marginTop: '0.5rem' }}>
          Seven calendar days ending on the selected date (UTC boundaries on the server). PRs and
          issues link to GitHub.
        </p>
      </TextContent>

      <FormGroup label="Week ending" fieldId="project-status-end-date">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'flex-end' }}>
          <TextInput
            id="project-status-end-date"
            type="date"
            value={draftEndDate}
            onChange={(value, event) => {
              let stringValue = '';
              if (typeof value === 'string') {
                stringValue = value;
              } else if (value && typeof value === 'object' && 'target' in value) {
                stringValue = value.target?.value || '';
              } else if (event && 'target' in event) {
                stringValue = event.target?.value || '';
              }
              setDraftEndDate(stringValue);
            }}
          />
          <Button variant="primary" onClick={onApplyDate}>
            Apply
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              const today = getLocalDateISOString();
              setDraftEndDate(today);
              setEndDate(today);
            }}
          >
            Today
          </Button>
        </div>
      </FormGroup>

      {windowLabel && !loading && !error && (
        <p style={{ marginTop: '1rem', fontWeight: 600 }}>Reporting window: {windowLabel}</p>
      )}

      {loading && (
        <div style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Spinner size="lg" />
          <span>Loading report…</span>
        </div>
      )}

      {error && (
        <Alert variant="danger" title="Could not load report" style={{ marginTop: '1rem' }}>
          {error}
        </Alert>
      )}

      {report && !loading && (
        <>
          <StatusSection heading="Merged pull requests" items={report.merged_pull_requests} />
          <StatusSection heading="New pull requests opened" items={report.opened_pull_requests} />
          <StatusSection heading="New issues opened" items={report.opened_issues} />
        </>
      )}
    </div>
  );
};

export default ProjectStatusPanel;
