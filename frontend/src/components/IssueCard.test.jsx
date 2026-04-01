// ai-generated: Cursor
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IssueCard from './IssueCard';
import * as api from '../services/api';
import assigneesCache from '../utils/assigneesCache';
import milestonesCache from '../utils/milestonesCache';

vi.mock('../services/api');

describe('IssueCard', () => {
  const mockIssue = {
    id: 1,
    number: 459,
    title: 'Add support for OpenAI Responses API',
    body: '**Is your feature request related to a problem?**\n\nYes, it is.',
    body_html:
      '<p><strong>Is your feature request related to a problem?</strong></p><p>Yes, it is.</p>',
    html_url: 'https://github.com/vllm-project/guidellm/issues/459',
    user: {
      login: 'tosokin',
      avatar_url: 'https://avatars.githubusercontent.com/u/180538846?v=4',
    },
    created_at: '2025-11-13T10:45:41Z',
    labels: [
      {
        id: 7015519659,
        name: 'enhancement',
        color: 'a2eeef',
      },
    ],
    comments: 0,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetchLabels to return an empty array by default
    api.fetchLabels.mockResolvedValue([]);
    // Mock fetchAssignees to return an empty array by default
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
    milestonesCache.data = [];
  });

  it('renders issue number and title', async () => {
    await act(async () => {
      render(<IssueCard issue={mockIssue} />);
    });
    await waitFor(() => {
      expect(screen.getByText('#459')).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Add support for OpenAI Responses API/)
    ).toBeInTheDocument();
  });

  it('renders issue number as a link', async () => {
    await act(async () => {
      render(<IssueCard issue={mockIssue} />);
    });
    await waitFor(() => {
      const link = screen.getByRole('link', { name: '#459' });
      expect(link).toHaveAttribute('href', mockIssue.html_url);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  it('shows expansion icon when body exists', async () => {
    await act(async () => {
      render(<IssueCard issue={mockIssue} />);
    });
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /show description/i })
      ).toBeInTheDocument();
    });
  });

  it('does not show expansion icon when body is absent', async () => {
    const issueWithoutBody = { ...mockIssue, body: null, body_html: null };
    await act(async () => {
      render(<IssueCard issue={issueWithoutBody} />);
    });
    await waitFor(() => {
      expect(
        screen.queryByRole('button', { name: /show description/i })
      ).not.toBeInTheDocument();
    });
  });

  it('expands and shows HTML body when expansion icon is clicked', async () => {
    const user = userEvent.setup();
    render(<IssueCard issue={mockIssue} />);
    const expandButton = screen.getByRole('button', {
      name: /show description/i,
    });
    await user.click(expandButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Is your feature request related to a problem/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /hide description/i })
      ).toBeInTheDocument();
    });
  });

  it('renders user avatar with correct src', async () => {
    await act(async () => {
      render(<IssueCard issue={mockIssue} />);
    });
    await waitFor(() => {
      const avatar = screen.getByAltText('tosokin');
      expect(avatar).toHaveAttribute('src', mockIssue.user.avatar_url);
    });
  });

  it('renders created date with days since', async () => {
    await act(async () => {
      render(<IssueCard issue={mockIssue} />);
    });
    await waitFor(() => {
      expect(screen.getByText(/\(/)).toBeInTheDocument(); // Should contain days ago
    });
  });

  it('handles missing body gracefully', async () => {
    const issueWithoutBody = { ...mockIssue, body: null, body_html: null };
    await act(async () => {
      render(<IssueCard issue={issueWithoutBody} />);
    });
    await waitFor(() => {
      expect(screen.getByText('#459')).toBeInTheDocument();
    });
  });

  it('handles missing user gracefully', async () => {
    const issueWithoutUser = { ...mockIssue, user: null };
    await act(async () => {
      render(<IssueCard issue={issueWithoutUser} />);
    });
    await waitFor(() => {
      expect(screen.getByText('Unknown')).toBeInTheDocument();
    });
  });

  it('renders labels when present', async () => {
    await act(async () => {
      render(<IssueCard issue={mockIssue} />);
    });
    await waitFor(() => {
      expect(screen.getByText('enhancement')).toBeInTheDocument();
    });
  });

  it('handles missing labels gracefully', async () => {
    const issueWithoutLabels = { ...mockIssue, labels: null };
    await act(async () => {
      render(<IssueCard issue={issueWithoutLabels} />);
    });
    await waitFor(() => {
      expect(screen.getByText('#459')).toBeInTheDocument();
    });
  });

  it('handles empty labels array', async () => {
    const issueWithEmptyLabels = { ...mockIssue, labels: [] };
    await act(async () => {
      render(<IssueCard issue={issueWithEmptyLabels} />);
    });
    await waitFor(() => {
      expect(screen.getByText('#459')).toBeInTheDocument();
    });
  });

  it('renders type chiclet when type is present', async () => {
    const issueWithType = {
      ...mockIssue,
      type: {
        name: 'Feature',
        color: 'blue',
        description: 'A request, idea, or new functionality',
      },
    };
    await act(async () => {
      render(<IssueCard issue={issueWithType} />);
    });
    await waitFor(() => {
      expect(screen.getByText('Feature')).toBeInTheDocument();
    });
  });

  it('does not render type chiclet when type is null', async () => {
    const issueWithoutType = { ...mockIssue, type: null };
    await act(async () => {
      render(<IssueCard issue={issueWithoutType} />);
    });
    await waitFor(() => {
      expect(screen.queryByText('Feature')).not.toBeInTheDocument();
    });
  });

  it('renders type chiclet with correct name and styling', async () => {
    const issueWithType = {
      ...mockIssue,
      type: {
        name: 'Feature',
        color: 'blue',
        description: 'A request, idea, or new functionality',
      },
    };
    await act(async () => {
      render(<IssueCard issue={issueWithType} />);
    });
    await waitFor(() => {
      const typeChiclet = screen.getByText('Feature');
      // Verify the type chiclet is present
      expect(typeChiclet).toBeInTheDocument();
      // Verify it's wrapped in a span (the chiclet container)
      const typeSpan = typeChiclet.closest('span');
      expect(typeSpan).toBeInTheDocument();
      // Verify the span has a background color style (exact format may vary)
      expect(typeSpan).toHaveAttribute('style');
      expect(typeSpan?.getAttribute('style')).toContain('blue');
    });
  });

  it('does not show comments control when description is not expanded', async () => {
    const issueWithComments = { ...mockIssue, comments: 2 };
    await act(async () => {
      render(<IssueCard issue={issueWithComments} />);
    });
    await waitFor(() => {
      expect(screen.queryByText(/Show Comments/i)).not.toBeInTheDocument();
    });
  });

  it('shows comments expansion control only when description is expanded', async () => {
    const user = userEvent.setup();
    const issueWithComments = { ...mockIssue, comments: 2 };
    await act(async () => {
      render(<IssueCard issue={issueWithComments} />);
    });

    // Comments control should not be visible initially
    await waitFor(() => {
      expect(screen.queryByText(/Show Comments/i)).not.toBeInTheDocument();
    });

    // Expand description via expansion icon
    const expandButton = screen.getByRole('button', {
      name: /show description/i,
    });
    await user.click(expandButton);

    // Now comments control should be visible
    await waitFor(() => {
      expect(screen.getByText(/Show Comments/i)).toBeInTheDocument();
    });
  });

  it('collapses comments when description is collapsed', async () => {
    const user = userEvent.setup();
    api.fetchComments.mockResolvedValue([]);
    const issueWithComments = { ...mockIssue, comments: 1 };
    await act(async () => {
      render(<IssueCard issue={issueWithComments} />);
    });

    // Expand description via expansion icon
    const expandButton = screen.getByRole('button', {
      name: /show description/i,
    });
    await user.click(expandButton);

    // Expand comments
    await waitFor(() => {
      expect(screen.getByText(/Show Comments/i)).toBeInTheDocument();
    });
    const commentsToggle = screen.getByText(/Show Comments/i);
    await user.click(commentsToggle);

    // Collapse description via expansion icon
    const collapseButton = screen.getByRole('button', {
      name: /hide description/i,
    });
    await user.click(collapseButton);

    // Comments should be hidden
    await waitFor(() => {
      expect(screen.queryByText(/Show Comments/i)).not.toBeInTheDocument();
    });
  });

  it('fetches and displays comments when comments section is expanded', async () => {
    const user = userEvent.setup();
    const mockComments = [
      {
        id: 1,
        body: 'This is a comment',
        body_html: '<p>This is a comment</p>',
        user: {
          login: 'testuser',
          avatar_url: 'https://avatar.url',
        },
        created_at: '2025-01-01T00:00:00Z',
      },
    ];
    api.fetchComments.mockResolvedValue(mockComments);

    const issueWithComments = { ...mockIssue, comments: 1 };
    await act(async () => {
      render(<IssueCard issue={issueWithComments} />);
    });

    // First expand description via expansion icon
    const expandButton = screen.getByRole('button', {
      name: /show description/i,
    });
    await user.click(expandButton);

    // Then expand comments
    await waitFor(() => {
      expect(screen.getByText(/Show Comments/i)).toBeInTheDocument();
    });
    const commentsToggle = screen.getByText(/Show Comments/i);
    await user.click(commentsToggle);

    await waitFor(() => {
      expect(api.fetchComments).toHaveBeenCalledWith(459);
      expect(screen.getByText('This is a comment')).toBeInTheDocument();
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });
  });

  it('calls onMilestoneChange with from/to when milestone is set', async () => {
    const user = userEvent.setup();
    const onMilestoneChange = vi.fn();
    milestonesCache.data = [{ number: 10, title: 'Next release' }];
    const issueWithMilestone = {
      ...mockIssue,
      milestone: { number: 6, title: 'Current' },
    };
    api.setIssueMilestone.mockResolvedValue({});

    await act(async () => {
      render(
        <table>
          <tbody>
            <IssueCard
              issue={issueWithMilestone}
              onMilestoneChange={onMilestoneChange}
            />
          </tbody>
        </table>
      );
    });

    await user.click(screen.getByRole('button', { name: 'Current' }));
    await user.click(screen.getByText('Next release'));

    await waitFor(() => {
      expect(api.setIssueMilestone).toHaveBeenCalledWith(459, 10);
      expect(onMilestoneChange).toHaveBeenCalledWith({
        fromMilestoneNumber: 6,
        toMilestoneNumber: 10,
      });
    });
  });

  it('calls onMilestoneChange with to null when milestone is removed', async () => {
    const user = userEvent.setup();
    const onMilestoneChange = vi.fn();
    milestonesCache.data = [{ number: 10, title: 'Other' }];
    const issueWithMilestone = {
      ...mockIssue,
      milestone: { number: 6, title: 'Current' },
    };
    api.removeIssueMilestone.mockResolvedValue({});

    await act(async () => {
      render(
        <table>
          <tbody>
            <IssueCard
              issue={issueWithMilestone}
              onMilestoneChange={onMilestoneChange}
            />
          </tbody>
        </table>
      );
    });

    await user.click(screen.getByRole('button', { name: 'Current' }));
    await user.click(screen.getByText('No Milestone', { selector: 'span' }));

    await waitFor(() => {
      expect(api.removeIssueMilestone).toHaveBeenCalledWith(459, 6);
      expect(onMilestoneChange).toHaveBeenCalledWith({
        fromMilestoneNumber: 6,
        toMilestoneNumber: null,
      });
    });
  });
});
