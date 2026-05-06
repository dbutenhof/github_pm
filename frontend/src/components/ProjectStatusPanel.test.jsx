// ai-generated: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProjectStatusPanel from './ProjectStatusPanel';
import * as api from '../services/api';
import * as clipboard from '../utils/clipboard';

vi.mock('../services/api');
vi.mock('../utils/clipboard', () => ({
  copyStatusSectionToClipboard: vi.fn().mockResolvedValue(undefined),
}));

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
    api.fetchProjectStatusReport.mockResolvedValue({
      start_date: '2025-04-04',
      end_date: '2025-04-10',
      merged_pull_requests: merged,
      opened_pull_requests: [],
      opened_issues: issues,
    });
  });

  it('loads report and renders linked rows', async () => {
    render(<ProjectStatusPanel />);

    await waitFor(() => {
      expect(api.fetchProjectStatusReport).toHaveBeenCalled();
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

  it('copy button passes section items to clipboard helper', async () => {
    const user = userEvent.setup();
    render(<ProjectStatusPanel />);

    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: 'Copy Merged pull requests to clipboard',
        })
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
});
