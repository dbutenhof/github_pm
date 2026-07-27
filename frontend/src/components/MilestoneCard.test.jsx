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

  it('renders Add Issue control under milestone header', async () => {
    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Add Issue' })
      ).toBeInTheDocument();
    });
  });

  it('opens create-issue modal from Add Issue', async () => {
    const user = userEvent.setup();
    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });
    await user.click(screen.getByRole('button', { name: 'Add Issue' }));
    expect(screen.getByText('Add issue to v0.6.0')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Issue title')).toBeInTheDocument();
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

  it('renders nested children when epic hierarchy is expanded', async () => {
    const user = userEvent.setup();
    const nested = {
      ...mockIssue,
      hierarchy_depth: 0,
      child_count: 1,
      children: [
        {
          id: 99,
          number: 500,
          title: 'Child Story',
          html_url: 'https://github.com/test/issue/500',
          user: { login: 'testuser', avatar_url: 'https://avatar.url' },
          created_at: '2025-01-01T00:00:00Z',
          labels: [],
          comments: 0,
          hierarchy_depth: 1,
          child_count: 0,
          children: [],
        },
      ],
    };
    api.fetchIssues.mockResolvedValue({
      issues: [nested],
      pull_requests: [],
    });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    await user.click(screen.getByRole('button', { name: /show issues/i }));
    await waitFor(() => {
      expect(screen.getByText(/Test Issue/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Child Story/)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Show sub-issues' }));
    await waitFor(() => {
      expect(screen.getByText(/Child Story/)).toBeInTheDocument();
    });
    expect(screen.getByText('Type')).toBeInTheDocument();
  });

  it('shows a newly created epic immediately from the POST response', async () => {
    const user = userEvent.setup();
    const created = {
      id: 900,
      number: 900,
      title: 'Brand New Epic',
      html_url: 'https://github.com/test/issue/900',
      user: { login: 'testuser', avatar_url: 'https://avatar.url' },
      created_at: '2025-01-01T00:00:00Z',
      labels: [],
      comments: 0,
    };
    api.createIssue.mockResolvedValue(created);
    // Simulate GitHub list lag: refetch would still be empty.
    api.fetchIssues.mockResolvedValue({ issues: [], pull_requests: [] });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    await user.click(screen.getByRole('button', { name: 'Add Issue' }));
    await user.type(
      screen.getByPlaceholderText('Issue title'),
      'Brand New Epic'
    );
    await user.click(screen.getByRole('button', { name: 'Create Issue' }));

    await waitFor(() => {
      expect(api.createIssue).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Brand New Epic',
          milestone: 6,
        })
      );
    });
    await waitFor(() => {
      expect(screen.getByText(/Brand New Epic/)).toBeInTheDocument();
    });
    // Creating before expand still loads the list (then inserts from POST).
    expect(api.fetchIssues).toHaveBeenCalledWith(6, []);
  });

  it('loads existing issues when creating before the list is expanded', async () => {
    const user = userEvent.setup();
    const existing = {
      ...mockIssue,
      title: 'Already Open Issue',
    };
    const created = {
      id: 900,
      number: 900,
      title: 'Brand New Epic',
      html_url: 'https://github.com/test/issue/900',
      user: { login: 'testuser', avatar_url: 'https://avatar.url' },
      created_at: '2025-01-01T00:00:00Z',
      labels: [],
      comments: 0,
    };
    api.createIssue.mockResolvedValue(created);
    api.fetchIssues.mockResolvedValue({
      issues: [existing],
      pull_requests: [],
    });

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    await user.click(screen.getByRole('button', { name: 'Add Issue' }));
    await user.type(
      screen.getByPlaceholderText('Issue title'),
      'Brand New Epic'
    );
    await user.click(screen.getByRole('button', { name: 'Create Issue' }));

    await waitFor(() => {
      expect(screen.getByText(/Brand New Epic/)).toBeInTheDocument();
      expect(screen.getByText(/Already Open Issue/)).toBeInTheDocument();
    });
    expect(api.fetchIssues).toHaveBeenCalledWith(6, []);
  });

  it('shows a newly created sub-issue under its parent immediately', async () => {
    const user = userEvent.setup();
    const parent = {
      ...mockIssue,
      hierarchy_depth: 0,
      child_count: 0,
      children: [],
    };
    const createdChild = {
      id: 901,
      number: 901,
      title: 'Fresh Sub-issue',
      html_url: 'https://github.com/test/issue/901',
      user: { login: 'testuser', avatar_url: 'https://avatar.url' },
      created_at: '2025-01-01T00:00:00Z',
      labels: [],
      comments: 0,
      parent_number: parent.number,
    };
    api.fetchIssues.mockResolvedValue({
      issues: [parent],
      pull_requests: [],
    });
    api.createIssue.mockResolvedValue(createdChild);

    await act(async () => {
      render(<MilestoneCard milestone={mockMilestone} />);
    });

    await user.click(screen.getByRole('button', { name: /show issues/i }));
    await waitFor(() => {
      expect(screen.getByText(/Test Issue/)).toBeInTheDocument();
    });

    const fetchCountAfterLoad = api.fetchIssues.mock.calls.length;

    await user.click(screen.getByRole('button', { name: 'Add sub-issue' }));
    await user.type(
      screen.getByPlaceholderText('Issue title'),
      'Fresh Sub-issue'
    );
    await user.click(screen.getByRole('button', { name: 'Create Issue' }));

    await waitFor(() => {
      expect(api.createIssue).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Fresh Sub-issue',
          parent_number: parent.number,
          milestone: 6,
        })
      );
    });
    await waitFor(() => {
      expect(screen.getByText(/Fresh Sub-issue/)).toBeInTheDocument();
    });
    expect(api.fetchIssues.mock.calls.length).toBe(fetchCountAfterLoad);
  });

  it('does not duplicate an issue when a stale cross-milestone relink action re-applies', async () => {
    const user = userEvent.setup();
    const parent = {
      id: 10,
      number: 10,
      title: 'Parent Epic',
      html_url: 'https://github.com/test/issue/10',
      user: { login: 'testuser', avatar_url: 'https://avatar.url' },
      created_at: '2025-01-01T00:00:00Z',
      labels: [],
      comments: 0,
      hierarchy_depth: 0,
      child_count: 1,
      children: [
        {
          id: 20,
          number: 20,
          title: 'Relinked Child',
          html_url: 'https://github.com/test/issue/20',
          user: { login: 'testuser', avatar_url: 'https://avatar.url' },
          created_at: '2025-01-01T00:00:00Z',
          labels: [],
          comments: 0,
          parent_number: 10,
          hierarchy_depth: 1,
          child_count: 0,
          children: [],
        },
      ],
    };
    // Fresh fetch already reflects the completed relink.
    api.fetchIssues.mockResolvedValue({
      issues: [parent],
      pull_requests: [],
    });

    const staleRelink = {
      key: 12345,
      type: 'relink',
      issueNumber: 20,
      parentNumber: 10,
      sourceMilestoneNumber: 99,
      targetMilestoneNumber: mockMilestone.number,
      issueSnapshot: {
        id: 20,
        number: 20,
        title: 'Relinked Child',
        children: [],
        child_count: 0,
      },
    };

    const { rerender } = await act(async () =>
      render(<MilestoneCard milestone={mockMilestone} hierarchyAction={null} />)
    );

    await user.click(screen.getByRole('button', { name: /show issues/i }));
    await waitFor(() => {
      expect(screen.getByText(/Parent Epic/)).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: 'Show sub-issues' }));
    await waitFor(() => {
      expect(screen.getByText(/Relinked Child/)).toBeInTheDocument();
    });
    expect(screen.getAllByText(/Relinked Child/)).toHaveLength(1);

    // Simulate remount/load completing while App still held a stale action.
    await act(async () => {
      rerender(
        <MilestoneCard
          milestone={mockMilestone}
          hierarchyAction={staleRelink}
        />
      );
    });

    await waitFor(() => {
      expect(screen.getAllByText(/Relinked Child/)).toHaveLength(1);
    });
  });
});
