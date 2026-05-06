// ai-generated: Cursor
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SdlcKpisPanel, { formatDaysAndHours } from './SdlcKpisPanel';

vi.mock('../services/api', () => ({
  fetchSdlcDelivery: vi.fn(),
  fetchEscapedDefectRate: vi.fn(),
  fetchBugBacklogDelta: vi.fn(),
}));

import {
  fetchSdlcDelivery,
  fetchEscapedDefectRate,
  fetchBugBacklogDelta,
} from '../services/api';

describe('formatDaysAndHours', () => {
  it('formats days and hours', () => {
    expect(formatDaysAndHours(86400)).toBe('1 d');
    expect(formatDaysAndHours(90000)).toBe('1 d 1 h');
    expect(formatDaysAndHours(3600)).toBe('1 h');
    expect(formatDaysAndHours(7200)).toBe('2 h');
  });

  it('uses < 1 h when under one hour', () => {
    expect(formatDaysAndHours(600)).toBe('< 1 h');
  });

  it('handles null and zero', () => {
    expect(formatDaysAndHours(null)).toBe('—');
    expect(formatDaysAndHours(0)).toBe('0 h');
  });
});

describe('SdlcKpisPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders title and loads metrics when expanded', async () => {
    const user = userEvent.setup();
    fetchSdlcDelivery.mockResolvedValue({
      window_days: 7,
      as_of: '2025-04-10T12:00:00Z',
      merged_pr_throughput: {
        total: 2,
        by_pr_type: { feature: 2, bug_fix: 0, docs: 0, unclassified: 0 },
        by_pr_size: { tiny: 2, small: 0, medium: 0, large: 0, unknown: 0 },
      },
      median_pr_cycle_time: {
        median_seconds: 3600,
        by_pr_type: { feature: 3600 },
        by_pr_size: { tiny: 3600 },
        pr_count: 2,
      },
      median_time_to_first_review: {
        median_seconds: 600,
        by_pr_type: { feature: 600 },
        by_pr_size: { tiny: 600 },
        included_pr_count: 1,
        eligible_pr_count: 1,
      },
    });
    fetchEscapedDefectRate.mockResolvedValue({
      as_of: '2025-04-10T12:00:00Z',
      releases: [
        {
          release: 'v1.0.0',
          feature_prs: 1,
          bug_fix_prs: 0,
          docs_prs: 0,
          escape_issues: 0,
          rate: 0,
          is_next_open: true,
        },
      ],
    });
    fetchBugBacklogDelta.mockResolvedValue({
      window_days: 7,
      as_of: '2025-04-10T12:00:00Z',
      bugs_opened: 1,
      bugs_closed: 0,
      net: 1,
    });

    render(<SdlcKpisPanel />);
    expect(screen.getByText('SDLC KPIs')).toBeInTheDocument();

    const toggle = screen.getByRole('button', {
      name: /show sdlc metrics/i,
    });
    await user.click(toggle);

    await waitFor(() => {
      expect(fetchSdlcDelivery).toHaveBeenCalled();
      expect(fetchEscapedDefectRate).toHaveBeenCalled();
      expect(fetchBugBacklogDelta).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText(/Merged PR throughput/i)).toBeInTheDocument();
    });
  });
});
