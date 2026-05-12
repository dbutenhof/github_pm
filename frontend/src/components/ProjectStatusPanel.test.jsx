// Generated-by: Cursor
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProjectStatusPanel from './ProjectStatusPanel';
import * as api from '../services/api';
import * as clipboard from '../utils/clipboard';

vi.mock('../services/api');
vi.mock('../utils/clipboard', () => ({
  copyStatusSectionToClipboard: vi.fn().mockResolvedValue(undefined),
}));

const STORAGE_START_KEY = 'pmStatsProjectStatusStartDate';
const STORAGE_END_KEY = 'pmStatsProjectStatusEndDate';

describe('ProjectStatusPanel', () => {
  const merged = [
    {
      number: 1,
      title: 'Fix bug',
      html_url: 'https://github.com/o/r/pull/1',
    },
  ];
  const issues = [
    {
      number: 2,
      title: 'Track work',
      html_url: 'https://github.com/o/r/issues/2',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.removeItem(STORAGE_START_KEY);
    localStorage.removeItem(STORAGE_END_KEY);
    localStorage.setItem(STORAGE_START_KEY, '2025-04-03');
    localStorage.setItem(STORAGE_END_KEY, '2025-04-10');
    api.fetchProjectStatusReport.mockResolvedValue({
      start_date: '2025-04-03',
      end_date: '2025-04-10',
      merged_pull_requests: merged,
      opened_pull_requests: [],
      opened_issues: issues,
      pr_backlog: [],
    });
  });

  afterEach(() => {
    localStorage.removeItem(STORAGE_START_KEY);
    localStorage.removeItem(STORAGE_END_KEY);
  });

  it('loads report and renders linked rows', async () => {
    render(<ProjectStatusPanel />);

    await waitFor(() => {
      expect(api.fetchProjectStatusReport).toHaveBeenCalledWith(
        '2025-04-03',
        '2025-04-10'
      );
    });

    const prLink = await screen.findByRole('link', { name: '#1' });
    expect(prLink).toHaveAttribute('href', 'https://github.com/o/r/pull/1');
    expect(screen.getByText('Fix bug')).toBeInTheDocument();

    const issueLink = screen.getByRole('link', { name: '#2' });
    expect(issueLink).toHaveAttribute(
      'href',
      'https://github.com/o/r/issues/2'
    );
    expect(screen.getByText('Track work')).toBeInTheDocument();
  });

  it('shows days since update in PR backlog section', async () => {
    api.fetchProjectStatusReport.mockResolvedValue({
      start_date: '2025-04-04',
      end_date: '2025-04-10',
      merged_pull_requests: [],
      opened_pull_requests: [],
      opened_issues: [],
      pr_backlog: [
        {
          number: 50,
          title: 'Stale open',
          html_url: 'https://github.com/o/r/pull/50',
          days_since_update: 7,
        },
      ],
    });
    render(<ProjectStatusPanel />);
    await waitFor(() => {
      expect(screen.getByText('Stale open')).toBeInTheDocument();
    });
    expect(screen.getByText('(7 days)')).toBeInTheDocument();
  });

  it('copy button passes section items to clipboard helper', async () => {
    const user = userEvent.setup();
    render(<ProjectStatusPanel />);

    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: 'Copy Merged pull requests to clipboard',
        })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { name: 'PR backlog' })
      ).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole('button', {
        name: 'Copy Merged pull requests to clipboard',
      })
    );
    expect(clipboard.copyStatusSectionToClipboard).toHaveBeenCalledWith(merged);

    await user.click(
      screen.getByRole('button', {
        name: 'Copy New issues opened to clipboard',
      })
    );
    expect(clipboard.copyStatusSectionToClipboard).toHaveBeenCalledWith(issues);
  });

  it('persists start and end dates when Apply is used', async () => {
    const user = userEvent.setup();
    api.fetchProjectStatusReport.mockResolvedValue({
      start_date: '2025-04-01',
      end_date: '2025-04-15',
      merged_pull_requests: [],
      opened_pull_requests: [],
      opened_issues: [],
      pr_backlog: [],
    });

    render(<ProjectStatusPanel />);

    await waitFor(() => {
      expect(api.fetchProjectStatusReport).toHaveBeenCalled();
    });

    await user.clear(screen.getByLabelText('Starting'));
    await user.type(screen.getByLabelText('Starting'), '2025-04-01');
    await user.clear(screen.getByLabelText('Ending'));
    await user.type(screen.getByLabelText('Ending'), '2025-04-15');
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() => {
      expect(api.fetchProjectStatusReport).toHaveBeenCalledWith(
        '2025-04-01',
        '2025-04-15'
      );
    });
    expect(localStorage.getItem(STORAGE_START_KEY)).toBe('2025-04-01');
    expect(localStorage.getItem(STORAGE_END_KEY)).toBe('2025-04-15');
  });
});
