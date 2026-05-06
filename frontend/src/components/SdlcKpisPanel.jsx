// ai-generated: Cursor
import React, { useState, useCallback, useEffect } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  Spinner,
  Alert,
  Title,
  Flex,
  FlexItem,
  TextInput,
  Tooltip,
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

const formatRate = (r) => {
  if (r == null || Number.isNaN(r)) {
    return '—';
  }
  return `${(r * 100).toFixed(1)}%`;
};

const formatWindowRange = (slice) => {
  if (!slice?.window_start || !slice?.window_end) {
    return '';
  }
  const a = new Date(slice.window_start).toLocaleString();
  const b = new Date(slice.window_end).toLocaleString();
  return `${a} → ${b}`;
};

const numericMax = (values) => {
  const nums = values
    .map((v) => (typeof v === 'number' && !Number.isNaN(v) ? v : null))
    .filter((v) => v != null);
  if (nums.length === 0) {
    return 1;
  }
  const m = Math.max(...nums.map((n) => Math.abs(n)));
  return m > 0 ? m : 1;
};

/**
 * @param {object} props
 * @param {Array<{ value: number | null, slice: object }>} props.bars
 * @param {(v: number | null) => string} props.formatValue
 * @param {(v: number | null, slice: object) => string} [props.formatHoverValue]
 * @param {number} [props.chartHeightPx]
 * @param {boolean} [props.compact] When true (default), bars stay grouped at fixed column width instead of stretching across the page.
 * @param {number} [props.barColumnWidthPx] Width reserved per week column in compact mode.
 */
const WeekBarChart = ({
  bars,
  formatValue,
  formatHoverValue,
  chartHeightPx = 120,
  compact = true,
  barColumnWidthPx = 48,
}) => {
  const vals = bars.map((b) =>
    b.value != null && !Number.isNaN(b.value) ? b.value : null
  );
  const maxV = numericMax(vals.filter((v) => v != null));
  const barFillWidth = Math.max(28, Math.min(40, barColumnWidthPx - 8));

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'stretch',
        gap: '0.35rem',
        marginTop: '0.35rem',
        ...(compact
          ? {
              width: 'fit-content',
              maxWidth: '100%',
              flexWrap: 'nowrap',
            }
          : {
              width: '100%',
            }),
      }}
    >
      {bars.map((b, i) => {
        const v = vals[i];
        const h =
          v == null ? 0 : Math.max(4, (Math.abs(v) / maxV) * chartHeightPx);
        const hoverMain =
          formatHoverValue != null
            ? formatHoverValue(v, b.slice)
            : formatValue(v);
        const tip = (
          <div>
            <div>{hoverMain}</div>
            <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
              {formatWindowRange(b.slice)}
            </div>
          </div>
        );
        return (
          <Tooltip key={i} content={tip}>
            <div
              style={{
                flex: compact ? '0 0 auto' : '1 1 0',
                width: compact ? barColumnWidthPx : undefined,
                minWidth: compact ? barColumnWidthPx : 0,
                maxWidth: compact ? barColumnWidthPx : undefined,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                cursor: 'default',
              }}
            >
              <div
                style={{
                  height: chartHeightPx,
                  width: '100%',
                  display: 'flex',
                  alignItems: 'flex-end',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    width: compact ? barFillWidth : 'min(52px, 90%)',
                    height: `${h}px`,
                    background: 'var(--pf-v5-chart-color-blue-300, #06c)',
                    borderRadius: '3px 3px 0 0',
                  }}
                />
              </div>
              <div
                style={{
                  fontSize: '0.75rem',
                  marginTop: '0.35rem',
                  textAlign: 'center',
                  lineHeight: 1.2,
                  wordBreak: 'break-word',
                  maxWidth: compact ? barColumnWidthPx + 8 : undefined,
                }}
              >
                {formatValue(v)}
              </div>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
};

const breakdownBoxStyle = {
  border: '1px solid var(--pf-v5-global--BorderColor--100, #d2d2d2)',
  borderRadius: '4px',
  padding: '0.75rem 0.85rem',
  backgroundColor: 'var(--pf-v5-global--BackgroundColor--150, #f5f5f5)',
  width: 'fit-content',
  maxWidth: '100%',
  flex: '0 1 auto',
  minWidth: 'min(100%, 12rem)',
};

const BreakdownWeekCharts = ({
  title,
  slices,
  byKey,
  chartKey,
  formatBarValue = (v) => (v == null ? '—' : String(v)),
}) => (
  <div style={{ marginTop: '0.75rem' }}>
    <Title headingLevel="h5" size="md">
      {title}
    </Title>
    <div
      style={{
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: '0.85rem',
        marginTop: '0.5rem',
        alignItems: 'flex-start',
      }}
    >
      {byKey.map((key) => (
        <div key={key} style={breakdownBoxStyle}>
          <strong
            style={{
              fontSize: '0.875rem',
              display: 'block',
              marginBottom: '0.35rem',
            }}
          >
            {key}
          </strong>
          <WeekBarChart
            chartHeightPx={72}
            bars={slices.map((slice) => ({
              slice,
              value: chartKey(slice, key),
            }))}
            formatValue={formatBarValue}
          />
        </div>
      ))}
    </div>
  </div>
);

const DEFAULT_WEEKS = 4;
const SDLC_WEEKS_STORAGE_KEY = 'pmStatsSdlcWeeks';

const readWeeksFromStorage = () => {
  try {
    const raw = localStorage.getItem(SDLC_WEEKS_STORAGE_KEY);
    const n = parseInt(raw, 10);
    if (Number.isFinite(n) && n >= 1 && n <= 52) {
      return n;
    }
  } catch (error) {
    console.error('Failed to read SDLC weeks from localStorage:', error);
  }
  return DEFAULT_WEEKS;
};

const SdlcKpisPanel = () => {
  const [weeksInput, setWeeksInput] = useState(() =>
    String(readWeeksFromStorage())
  );
  const [weeks, setWeeks] = useState(() => readWeeksFromStorage());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [delivery, setDelivery] = useState(null);
  const [escaped, setEscaped] = useState(null);
  const [backlog, setBacklog] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      fetchSdlcDelivery(weeks, 7),
      fetchEscapedDefectRate(weeks, 7),
      fetchBugBacklogDelta(weeks, 7),
    ])
      .then(([d, e, b]) => {
        setDelivery(d);
        setEscaped(e);
        setBacklog(b);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || String(err));
        setLoading(false);
      });
  }, [weeks]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    try {
      localStorage.setItem(SDLC_WEEKS_STORAGE_KEY, String(weeks));
    } catch (error) {
      console.error('Failed to save SDLC weeks to localStorage:', error);
    }
  }, [weeks]);

  const applyWeeksFromInput = () => {
    const n = parseInt(weeksInput, 10);
    if (Number.isFinite(n) && n >= 1 && n <= 52) {
      setWeeks(n);
      setWeeksInput(String(n));
    } else {
      setWeeksInput(String(weeks));
    }
  };

  const deliverySlices = delivery?.slices ?? [];
  const escapedSlices = escaped?.slices ?? [];
  const backlogSlices = backlog?.slices ?? [];

  const throughputKeys = deliverySlices[0]
    ? [...Object.keys(deliverySlices[0].merged_pr_throughput?.by_pr_type || {})]
    : [];
  const sizeKeys = deliverySlices[0]
    ? [...Object.keys(deliverySlices[0].merged_pr_throughput?.by_pr_size || {})]
    : [];

  return (
    <Card>
      <CardHeader>
        <Flex
          justifyContent={{ default: 'justifyContentSpaceBetween' }}
          alignItems={{ default: 'alignItemsCenter' }}
          style={{ width: '100%' }}
        >
          <FlexItem>
            <CardTitle>SDLC KPIs</CardTitle>
          </FlexItem>
          <FlexItem>
            <Flex
              alignItems={{ default: 'alignItemsCenter' }}
              spaceItems={{ default: 'spaceItemsSm' }}
              style={{ flexWrap: 'nowrap', whiteSpace: 'nowrap' }}
            >
              <label
                htmlFor="sdlc-weeks-input"
                style={{ fontSize: '0.875rem', margin: 0 }}
              >
                Weeks:
              </label>
              <TextInput
                id="sdlc-weeks-input"
                type="number"
                value={weeksInput}
                onChange={(_e, val) => setWeeksInput(val)}
                onBlur={applyWeeksFromInput}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    applyWeeksFromInput();
                  }
                }}
                style={{ width: '4.5rem' }}
              />
            </Flex>
          </FlexItem>
        </Flex>
      </CardHeader>
      <CardBody>
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
        {!loading &&
          !error &&
          delivery &&
          escaped &&
          backlog &&
          deliverySlices.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
              }}
            >
              <section>
                <Title headingLevel="h4" size="lg">
                  Delivery (per {delivery.week_days || 7}-day window)
                </Title>
                <p style={{ color: '#6a6e73', fontSize: '0.875rem' }}>
                  {deliverySlices.length} week
                  {deliverySlices.length === 1 ? '' : 's'} (oldest left → newest
                  right). As of{' '}
                  {new Date(
                    deliverySlices[deliverySlices.length - 1]?.as_of
                  ).toLocaleString()}
                </p>

                <Title
                  headingLevel="h5"
                  size="md"
                  style={{ marginTop: '0.75rem' }}
                >
                  1. Merged PR throughput (total)
                </Title>
                <WeekBarChart
                  bars={deliverySlices.map((slice) => ({
                    slice,
                    value: slice.merged_pr_throughput?.total ?? 0,
                  }))}
                  formatValue={(v) => String(v ?? 0)}
                />

                <BreakdownWeekCharts
                  title="Throughput by PR type"
                  slices={deliverySlices}
                  byKey={throughputKeys}
                  chartKey={(slice, key) =>
                    slice.merged_pr_throughput?.by_pr_type?.[key] ?? 0
                  }
                />
                <BreakdownWeekCharts
                  title="Throughput by PR size"
                  slices={deliverySlices}
                  byKey={sizeKeys}
                  chartKey={(slice, key) =>
                    slice.merged_pr_throughput?.by_pr_size?.[key] ?? 0
                  }
                />

                <Title
                  headingLevel="h5"
                  size="md"
                  style={{ marginTop: '1rem' }}
                >
                  2. Median PR cycle time (open → merge)
                </Title>
                <WeekBarChart
                  bars={deliverySlices.map((slice) => ({
                    slice,
                    value: slice.median_pr_cycle_time?.median_seconds,
                  }))}
                  formatValue={(v) => formatDaysAndHours(v)}
                  formatHoverValue={(v, slice) =>
                    v == null
                      ? '—'
                      : `${formatDaysAndHours(v)} (${slice.median_pr_cycle_time?.pr_count ?? 0} PRs)`
                  }
                />
                <BreakdownWeekCharts
                  title="Median cycle time by PR type"
                  slices={deliverySlices}
                  byKey={[
                    ...Object.keys(
                      deliverySlices[0].median_pr_cycle_time?.by_pr_type || {}
                    ),
                  ]}
                  chartKey={(slice, key) =>
                    slice.median_pr_cycle_time?.by_pr_type?.[key] ?? null
                  }
                  formatBarValue={(v) => formatDaysAndHours(v)}
                />
                <BreakdownWeekCharts
                  title="Median cycle time by PR size"
                  slices={deliverySlices}
                  byKey={[
                    ...Object.keys(
                      deliverySlices[0].median_pr_cycle_time?.by_pr_size || {}
                    ),
                  ]}
                  chartKey={(slice, key) =>
                    slice.median_pr_cycle_time?.by_pr_size?.[key] ?? null
                  }
                  formatBarValue={(v) => formatDaysAndHours(v)}
                />

                <Title
                  headingLevel="h5"
                  size="md"
                  style={{ marginTop: '1rem' }}
                >
                  3. Median time to first human review
                </Title>
                <p style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
                  Eligible / included PR counts vary by week (see tooltips).
                </p>
                <WeekBarChart
                  bars={deliverySlices.map((slice) => ({
                    slice,
                    value: slice.median_time_to_first_review?.median_seconds,
                  }))}
                  formatValue={(v) => formatDaysAndHours(v)}
                  formatHoverValue={(v, slice) =>
                    v == null
                      ? '—'
                      : `${formatDaysAndHours(v)} (eligible ${slice.median_time_to_first_review?.eligible_pr_count ?? 0}, with review ${slice.median_time_to_first_review?.included_pr_count ?? 0})`
                  }
                />
                <BreakdownWeekCharts
                  title="Median time to first review by PR type"
                  slices={deliverySlices}
                  byKey={[
                    ...Object.keys(
                      deliverySlices[0].median_time_to_first_review
                        ?.by_pr_type || {}
                    ),
                  ]}
                  chartKey={(slice, key) =>
                    slice.median_time_to_first_review?.by_pr_type?.[key] ?? null
                  }
                  formatBarValue={(v) => formatDaysAndHours(v)}
                />
                <BreakdownWeekCharts
                  title="Median time to first review by PR size"
                  slices={deliverySlices}
                  byKey={[
                    ...Object.keys(
                      deliverySlices[0].median_time_to_first_review
                        ?.by_pr_size || {}
                    ),
                  ]}
                  chartKey={(slice, key) =>
                    slice.median_time_to_first_review?.by_pr_size?.[key] ?? null
                  }
                  formatBarValue={(v) => formatDaysAndHours(v)}
                />
              </section>

              <section>
                <Title headingLevel="h4" size="lg">
                  Quality
                </Title>

                <Title
                  headingLevel="h5"
                  size="md"
                  style={{ marginTop: '0.5rem' }}
                >
                  4. Escaped defect rate (per release milestone, incremental per
                  week)
                </Title>
                <p style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
                  Milestone rows follow current repo semver selection. Each bar
                  counts escapes <strong>created</strong> and PRs{' '}
                  <strong>merged</strong> into the milestone within that week.
                  As of{' '}
                  {new Date(
                    escapedSlices[escapedSlices.length - 1]?.as_of
                  ).toLocaleString()}
                  .
                </p>
                {(escapedSlices[0]?.releases || []).map((row, idx) => (
                  <div
                    key={`${row.release}-${row.is_next_open ? 'next' : 'closed'}`}
                    style={{ marginTop: '0.75rem' }}
                  >
                    <Title headingLevel="h6" size="md">
                      {row.release}
                      {row.is_next_open ? (
                        <span style={{ color: '#6a6e73', fontWeight: 400 }}>
                          {' '}
                          (next open / pre-release)
                        </span>
                      ) : null}
                    </Title>
                    <div
                      style={{ fontSize: '0.8rem', marginBottom: '0.25rem' }}
                    >
                      Rate (escapes ÷ feature+bug+docs PRs merged in window)
                    </div>
                    <WeekBarChart
                      bars={escapedSlices.map((slice) => {
                        const r = slice.releases[idx];
                        return {
                          slice,
                          value: r?.rate != null ? r.rate * 100 : null,
                        };
                      })}
                      formatValue={(v) =>
                        v == null ? '—' : `${Number(v).toFixed(1)}%`
                      }
                      formatHoverValue={(v, slice) => {
                        const r = slice.releases[idx];
                        if (!r) {
                          return '—';
                        }
                        return `${formatRate(r.rate)} — ${r.escape_issues ?? 0} escape(s); features ${r.feature_prs}, bugs ${r.bug_fix_prs}, docs ${r.docs_prs ?? 0}`;
                      }}
                    />
                  </div>
                ))}
              </section>

              <section>
                <Title
                  headingLevel="h5"
                  size="md"
                  style={{ marginTop: '1rem' }}
                >
                  5. Open bug backlog (opened / closed / net per week)
                </Title>
                <Title
                  headingLevel="h6"
                  size="sm"
                  style={{ marginTop: '0.5rem' }}
                >
                  Opened
                </Title>
                <WeekBarChart
                  bars={backlogSlices.map((slice) => ({
                    slice,
                    value: slice.bugs_opened,
                  }))}
                  formatValue={(v) => String(v ?? 0)}
                />
                <Title
                  headingLevel="h6"
                  size="sm"
                  style={{ marginTop: '0.75rem' }}
                >
                  Closed
                </Title>
                <WeekBarChart
                  bars={backlogSlices.map((slice) => ({
                    slice,
                    value: slice.bugs_closed,
                  }))}
                  formatValue={(v) => String(v ?? 0)}
                />
                <Title
                  headingLevel="h6"
                  size="sm"
                  style={{ marginTop: '0.75rem' }}
                >
                  Net
                </Title>
                <WeekBarChart
                  bars={backlogSlices.map((slice) => ({
                    slice,
                    value: slice.net,
                  }))}
                  formatValue={(v) => String(v ?? 0)}
                />
              </section>
            </div>
          )}
      </CardBody>
    </Card>
  );
};

export default SdlcKpisPanel;
