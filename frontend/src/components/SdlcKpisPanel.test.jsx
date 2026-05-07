// Generated-by: Cursor
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
    localStorage.removeItem('pmStatsSdlcWeeks');
  });

  const deliverySlice = {
    window_days: 7,
    window_start: '2025-04-03T12:00:00Z',
    window_end: '2025-04-10T12:00:00Z',
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
  };

  const makeSeriesMocks = (sliceCount) => {
    const slices = Array.from({ length: sliceCount }, () => ({
      ...deliverySlice,
    }));
    fetchSdlcDelivery.mockResolvedValue({
      weeks: sliceCount,
      week_days: 7,
      slices,
    });
    const escapeSlice = {
      window_start: '2025-04-03T12:00:00Z',
      window_end: '2025-04-10T12:00:00Z',
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
    };
    const backlogSlice = {
      window_days: 7,
      window_start: '2025-04-03T12:00:00Z',
      window_end: '2025-04-10T12:00:00Z',
      as_of: '2025-04-10T12:00:00Z',
      bugs_opened: 1,
      bugs_closed: 0,
      net: 1,
    };
    fetchEscapedDefectRate.mockResolvedValue({
      weeks: sliceCount,
      week_days: 7,
      slices: Array.from({ length: sliceCount }, () => ({ ...escapeSlice })),
    });
    fetchBugBacklogDelta.mockResolvedValue({
      weeks: sliceCount,
      week_days: 7,
      slices: Array.from({ length: sliceCount }, () => ({ ...backlogSlice })),
    });
  };

  it('renders title and loads metrics on mount', async () => {
    makeSeriesMocks(1);

    render(<SdlcKpisPanel />);
    expect(screen.getByText('SDLC KPIs')).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchSdlcDelivery).toHaveBeenCalledWith(4, 7);
      expect(fetchEscapedDefectRate).toHaveBeenCalledWith(4, 7);
      expect(fetchBugBacklogDelta).toHaveBeenCalledWith(4, 7);
    });

    await waitFor(() => {
      expect(screen.getByText(/Merged PR throughput/i)).toBeInTheDocument();
    });
  });

  it('loads week count from localStorage', async () => {
    localStorage.setItem('pmStatsSdlcWeeks', '8');
    makeSeriesMocks(8);

    render(<SdlcKpisPanel />);

    await waitFor(() => {
      expect(fetchSdlcDelivery).toHaveBeenCalledWith(8, 7);
      expect(fetchEscapedDefectRate).toHaveBeenCalledWith(8, 7);
      expect(fetchBugBacklogDelta).toHaveBeenCalledWith(8, 7);
    });
  });

  it('persists week count to localStorage when applied', async () => {
    const user = userEvent.setup();
    makeSeriesMocks(4);

    render(<SdlcKpisPanel />);

    await waitFor(() => {
      expect(screen.getByLabelText(/weeks/i)).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/weeks/i);
    await user.clear(input);
    await user.type(input, '6');
    await user.tab();

    await waitFor(() => {
      expect(localStorage.getItem('pmStatsSdlcWeeks')).toBe('6');
    });
    expect(fetchSdlcDelivery).toHaveBeenLastCalledWith(6, 7);
  });
});
