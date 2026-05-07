// Generated-by: Cursor
import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
import {
  addDaysToLocalDateISO,
  formatDate,
  getLocalDateISOString,
} from '../utils/dateUtils';

const STORAGE_START_KEY = 'pmStatsProjectStatusStartDate';
const STORAGE_END_KEY = 'pmStatsProjectStatusEndDate';

const readStoredDate = (key) => {
  try {
    const raw = localStorage.getItem(key);
    if (raw && /^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      return raw;
    }
  } catch (error) {
    console.error(`Failed to read ${key} from localStorage:`, error);
  }
  return null;
};

const getInitialDateRange = () => {
  const today = getLocalDateISOString();
  const storedEnd = readStoredDate(STORAGE_END_KEY);
  const storedStart = readStoredDate(STORAGE_START_KEY);
  const end = storedEnd ?? today;
  const start = storedStart ?? addDaysToLocalDateISO(end, -7);
  if (start > end) {
    return { start: addDaysToLocalDateISO(end, -7), end };
  }
  return { start, end };
};

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
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            flexWrap: 'wrap',
          }}
        >
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
              <li
                key={`${heading}-${row.number}`}
                style={{ marginBottom: '0.35rem' }}
              >
                <a
                  href={row.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
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
  const initial = useMemo(() => getInitialDateRange(), []);

  const [startDate, setStartDate] = useState(initial.start);
  const [endDate, setEndDate] = useState(initial.end);
  const [draftStartDate, setDraftStartDate] = useState(initial.start);
  const [draftEndDate, setDraftEndDate] = useState(initial.end);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);

  const load = useCallback(async (startIso, endIso) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjectStatusReport(startIso, endIso);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e?.message || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(startDate, endDate);
  }, [startDate, endDate, load]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_START_KEY, startDate);
      localStorage.setItem(STORAGE_END_KEY, endDate);
    } catch (error) {
      console.error('Failed to save project status date range:', error);
    }
  }, [startDate, endDate]);

  const onApply = () => {
    if (draftStartDate > draftEndDate) {
      setDraftStartDate(startDate);
      setDraftEndDate(endDate);
      return;
    }
    setStartDate(draftStartDate);
    setEndDate(draftEndDate);
  };

  const windowLabel =
    report?.start_date && report?.end_date
      ? `${formatDate(`${report.start_date}T12:00:00Z`)} — ${formatDate(`${report.end_date}T12:00:00Z`)}`
      : '';

  const dateInputOnChange = (setter) => (value, event) => {
    let stringValue = '';
    if (typeof value === 'string') {
      stringValue = value;
    } else if (value && typeof value === 'object' && 'target' in value) {
      stringValue = value.target?.value || '';
    } else if (event && 'target' in event) {
      stringValue = event.target?.value || '';
    }
    setter(stringValue);
  };

  return (
    <div style={{ maxWidth: '960px' }}>
      <TextContent>
        <Title headingLevel="h2" size="xl">
          Project status
        </Title>
        <p style={{ marginTop: '0.5rem' }}>
          Choose the first and last calendar day to include (UTC boundaries on
          the server). Defaults match ending today and starting seven days
          earlier. PRs and issues link to GitHub.
        </p>
      </TextContent>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1rem',
          alignItems: 'flex-end',
          marginTop: '0.5rem',
        }}
      >
        <FormGroup label="Starting" fieldId="project-status-start-date">
          <TextInput
            id="project-status-start-date"
            type="date"
            value={draftStartDate}
            onChange={dateInputOnChange(setDraftStartDate)}
          />
        </FormGroup>
        <FormGroup label="Ending" fieldId="project-status-end-date">
          <TextInput
            id="project-status-end-date"
            type="date"
            value={draftEndDate}
            onChange={dateInputOnChange(setDraftEndDate)}
          />
        </FormGroup>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.5rem',
            alignItems: 'flex-end',
          }}
        >
          <Button variant="primary" onClick={onApply}>
            Apply
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              const today = getLocalDateISOString();
              const start = addDaysToLocalDateISO(today, -7);
              setDraftStartDate(start);
              setDraftEndDate(today);
              setStartDate(start);
              setEndDate(today);
            }}
          >
            Today
          </Button>
        </div>
      </div>

      {windowLabel && !loading && !error && (
        <p style={{ marginTop: '1rem', fontWeight: 600 }}>
          Reporting window: {windowLabel}
        </p>
      )}

      {loading && (
        <div
          style={{
            marginTop: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}
        >
          <Spinner size="lg" />
          <span>Loading report…</span>
        </div>
      )}

      {error && (
        <Alert
          variant="danger"
          title="Could not load report"
          style={{ marginTop: '1rem' }}
        >
          {error}
        </Alert>
      )}

      {report && !loading && (
        <>
          <StatusSection
            heading="Merged pull requests"
            items={report.merged_pull_requests}
          />
          <StatusSection
            heading="New pull requests opened"
            items={report.opened_pull_requests}
          />
          <StatusSection
            heading="New issues opened"
            items={report.opened_issues}
          />
        </>
      )}
    </div>
  );
};

export default ProjectStatusPanel;
