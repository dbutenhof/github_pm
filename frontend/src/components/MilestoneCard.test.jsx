// Generated-by: Cursor
// Assisted-by: Cursor
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MilestoneCard from './MilestoneCard';
import * as api from '../services/api';
import assigneesCache from '../utils/assigneesCache';

vi.mock('../services/api');

describe('MilestoneCard', () => {
  const mockMilestone = {
    number: 6,
    title: 'v0.6.0',
    description: 'Version 0.6.0',
    due_on: '2025-12-31T00:00:00Z',
  };

  const mockIssue = {
    id: 1,
    number: 459,
    title: 'Test Issue',
    body: 'Issue body',
    html_url: 'https://github.com/test/issue/459',
    user: { login: 'testuser', avatar_url: 'https://avatar.url' },
    created_at: '2025-01-01T00:00:00Z',
    labels: [],
    comments: 0,
  };

  const mockPr = {
    id: 2,
    number: 460,
    title: 'Test PR',
    body: 'PR body',
    html_url: 'https://github.com/test/pull/460',
    user: { login: 'testuser', avatar_url: 'https://avatar.url' },
    created_at: '2025-01-01T00:00:00Z',
    labels: [],
    comments: 0,
    pull_request: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchLabels.mockResolvedValue([]);
    api.fetchAssignees.mockResolvedValue([]);
    // Clear assignees cache before each test
    assigneesCache.data = [];
    assigneesCache.loading = false;
    assigneesCache.error = null;
    assigneesCache.promise = null;
  });

  afterEach(() => {
    // Clear assignees cache after each test
    assigneesCache.data = [];
    assigneesCache.loading = false;
    assigneesCache.error = null;
    assigneesCache.promise = null;
  });

  it('renders milestone title', async () => {
    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    await waitFor(() => {
      expect(screen.getByText('v0.6.0')).toBeInTheDocument();
    });
  });

  it('renders milestone description when provided', async () => {
    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    await waitFor(() => {
      expect(screen.getByText('Version 0.6.0')).toBeInTheDocument();
    });
  });

  it('renders due date when provided', async () => {
    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    await waitFor(() => {
      expect(screen.getByText(/Due:/i)).toBeInTheDocument();
    });
  });

  it('expands and fetches issues when clicked', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue({
      issues: [mockIssue],
      pull_requests: [],
    });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(api.fetchIssues).toHaveBeenCalledWith(6, []);
    });

    await waitFor(
      () => {
        expect(screen.getByText(/Test Issue/)).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows loading spinner while fetching issues', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockImplementation(() => new Promise(() => {}));

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockRejectedValue(new Error('Fetch failed'));

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText(/Error loading issues/i)).toBeInTheDocument();
    });
  });

  it('shows empty message when no issues', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue({ issues: [], pull_requests: [] });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText(/No issues found/i)).toBeInTheDocument();
    });
  });

  it('does not show PR expander before issues are loaded', async () => {
    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    expect(
      screen.queryByRole('button', { name: /show \d+ prs?/i })
    ).not.toBeInTheDocument();
  });

  it('shows closed PR expander when pull requests are discovered', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue({
      issues: [mockIssue],
      pull_requests: [mockPr],
    });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    await user.click(screen.getByRole('button', { name: /show issues/i }));

    await waitFor(() => {
      expect(screen.getByText(/Test Issue/)).toBeInTheDocument();
    });

    const prToggle = screen.getByRole('button', { name: /show 1 pr/i });
    expect(prToggle).toBeInTheDocument();
    expect(prToggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(prToggle);

    await waitFor(() => {
      expect(prToggle).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByText(/Test PR/)).toBeInTheDocument();
    });
    expect(
      screen.getByRole('button', { name: /hide 1 pr/i })
    ).toBeInTheDocument();
  });

  it('does not show PR expander when there are no pull requests', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue({
      issues: [mockIssue],
      pull_requests: [],
    });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    await user.click(screen.getByRole('button', { name: /show issues/i }));

    await waitFor(() => {
      expect(screen.getByText(/Test Issue/)).toBeInTheDocument();
    });

    expect(
      screen.queryByRole('button', { name: /show \d+ prs?/i })
    ).not.toBeInTheDocument();
  });

  it('refetches issues when issueMilestoneRefresh targets this milestone', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue({
      issues: [mockIssue],
      pull_requests: [],
    });

    const onIssueMilestoneMoved = vi.fn();
    const initialRefresh = { key: 0, milestoneNumbers: [] };

    const { rerender } = await act(async () =>
      render(
        <MilestoneCard
          milestone={mockMilestone}
          issueMilestoneRefresh={initialRefresh}
          onIssueMilestoneMoved={onIssueMilestoneMoved}
        />
      )
    );

    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(api.fetchIssues).toHaveBeenCalledTimes(1);
    });

    await act(async () => {
      rerender(
        <MilestoneCard
          milestone={mockMilestone}
          issueMilestoneRefresh={{ key: 1, milestoneNumbers: [6] }}
          onIssueMilestoneMoved={onIssueMilestoneMoved}
        />
      );
    });

    await waitFor(() => {
      expect(api.fetchIssues).toHaveBeenCalledTimes(2);
    });
    expect(api.fetchIssues).toHaveBeenLastCalledWith(6, []);
  });

  it('refetches loaded milestones even when issues section is collapsed', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue({
      issues: [mockIssue],
      pull_requests: [],
    });

    const { rerender } = await act(async () =>
      render(
        <MilestoneCard
          milestone={mockMilestone}
          issueMilestoneRefresh={{ key: 0, milestoneNumbers: [] }}
        />
      )
    );

    await user.click(screen.getByRole('button', { name: /show issues/i }));
    await waitFor(() => {
      expect(api.fetchIssues).toHaveBeenCalledTimes(1);
    });

    // Collapse issues section
    await user.click(screen.getByRole('button', { name: /hide 1 issue/i }));

    await act(async () => {
      rerender(
        <MilestoneCard
          milestone={mockMilestone}
          issueMilestoneRefresh={{ key: 1, milestoneNumbers: [6] }}
        />
      );
    });

    await waitFor(() => {
      expect(api.fetchIssues).toHaveBeenCalledTimes(2);
    });
  });
});
