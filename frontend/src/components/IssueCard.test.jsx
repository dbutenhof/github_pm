// ai-generated: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IssueCard from './IssueCard';
import * as api from '../services/api';

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
  });

  it('renders issue number and title', () => {
    render(<IssueCard issue={mockIssue} />);
    expect(screen.getByText('#459')).toBeInTheDocument();
    expect(
      screen.getByText(/Add support for OpenAI Responses API/)
    ).toBeInTheDocument();
  });

  it('renders issue number as a link', () => {
    render(<IssueCard issue={mockIssue} />);
    const link = screen.getByRole('link', { name: '#459' });
    expect(link).toHaveAttribute('href', mockIssue.html_url);
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('shows description toggle when body exists', () => {
    render(<IssueCard issue={mockIssue} />);
    expect(screen.getByText('Show Description')).toBeInTheDocument();
  });

  it('shows comment count in toggle text when comments exist', () => {
    const issueWithComments = { ...mockIssue, comments: 5 };
    render(<IssueCard issue={issueWithComments} />);
    expect(
      screen.getByText('Show Description (5 comments)')
    ).toBeInTheDocument();
  });

  it('shows singular comment in toggle text for 1 comment', () => {
    const issueWithOneComment = { ...mockIssue, comments: 1 };
    render(<IssueCard issue={issueWithOneComment} />);
    expect(
      screen.getByText('Show Description (1 comment)')
    ).toBeInTheDocument();
  });

  it('does not show comment count when comments is 0', () => {
    const issueWithNoComments = { ...mockIssue, comments: 0 };
    render(<IssueCard issue={issueWithNoComments} />);
    expect(screen.getByText('Show Description')).toBeInTheDocument();
    expect(screen.queryByText(/comment/)).not.toBeInTheDocument();
  });

  it('expands and shows HTML body when toggle is clicked', async () => {
    const user = userEvent.setup();
    render(<IssueCard issue={mockIssue} />);
    const toggleButton = screen.getByText('Show Description');
    await user.click(toggleButton);

    await waitFor(() => {
      // The HTML content should be rendered, check for the text content
      expect(
        screen.getByText(/Is your feature request related to a problem/i)
      ).toBeInTheDocument();
      expect(screen.getByText('Hide Description')).toBeInTheDocument();
    });
  });

  it('shows comment count in expanded toggle text when comments exist', async () => {
    const user = userEvent.setup();
    const issueWithComments = { ...mockIssue, comments: 3 };
    render(<IssueCard issue={issueWithComments} />);
    const toggleButton = screen.getByText('Show Description (3 comments)');
    await user.click(toggleButton);

    await waitFor(() => {
      expect(
        screen.getByText('Hide Description (3 comments)')
      ).toBeInTheDocument();
    });
  });

  it('renders user information', () => {
    render(<IssueCard issue={mockIssue} />);
    expect(screen.getByText('tosokin')).toBeInTheDocument();
  });

  it('renders user avatar', () => {
    render(<IssueCard issue={mockIssue} />);
    const avatar = screen.getByAltText('tosokin');
    expect(avatar).toHaveAttribute('src', mockIssue.user.avatar_url);
  });

  it('renders created date with days since', () => {
    render(<IssueCard issue={mockIssue} />);
    expect(screen.getByText(/\(/)).toBeInTheDocument(); // Should contain days ago
  });

  it('handles missing body gracefully', () => {
    const issueWithoutBody = { ...mockIssue, body: null, body_html: null };
    render(<IssueCard issue={issueWithoutBody} />);
    expect(screen.getByText('#459')).toBeInTheDocument();
  });

  it('handles missing user gracefully', () => {
    const issueWithoutUser = { ...mockIssue, user: null };
    render(<IssueCard issue={issueWithoutUser} />);
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('renders labels when present', () => {
    render(<IssueCard issue={mockIssue} />);
    expect(screen.getByText('enhancement')).toBeInTheDocument();
  });

  it('handles missing labels gracefully', () => {
    const issueWithoutLabels = { ...mockIssue, labels: null };
    render(<IssueCard issue={issueWithoutLabels} />);
    expect(screen.getByText('#459')).toBeInTheDocument();
  });

  it('handles empty labels array', () => {
    const issueWithEmptyLabels = { ...mockIssue, labels: [] };
    render(<IssueCard issue={issueWithEmptyLabels} />);
    expect(screen.getByText('#459')).toBeInTheDocument();
  });

  it('renders type chiclet when type is present', () => {
    const issueWithType = {
      ...mockIssue,
      type: {
        name: 'Feature',
        color: 'blue',
        description: 'A request, idea, or new functionality',
      },
    };
    render(<IssueCard issue={issueWithType} />);
    expect(screen.getByText('Feature')).toBeInTheDocument();
  });

  it('does not render type chiclet when type is null', () => {
    const issueWithoutType = { ...mockIssue, type: null };
    render(<IssueCard issue={issueWithoutType} />);
    expect(screen.queryByText('Feature')).not.toBeInTheDocument();
  });

  it('renders type chiclet with correct name and styling', () => {
    const issueWithType = {
      ...mockIssue,
      type: {
        name: 'Feature',
        color: 'blue',
        description: 'A request, idea, or new functionality',
      },
    };
    render(<IssueCard issue={issueWithType} />);
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

  it('does not show comments control when description is not expanded', () => {
    const issueWithComments = { ...mockIssue, comments: 2 };
    render(<IssueCard issue={issueWithComments} />);
    expect(screen.queryByText(/Show Comments/i)).not.toBeInTheDocument();
  });

  it('shows comments expansion control only when description is expanded', async () => {
    const user = userEvent.setup();
    const issueWithComments = { ...mockIssue, comments: 2 };
    render(<IssueCard issue={issueWithComments} />);

    // Comments control should not be visible initially
    expect(screen.queryByText(/Show Comments/i)).not.toBeInTheDocument();

    // Expand description
    const descriptionToggle = screen.getByText('Show Description (2 comments)');
    await user.click(descriptionToggle);

    // Now comments control should be visible
    await waitFor(() => {
      expect(screen.getByText(/Show Comments/i)).toBeInTheDocument();
    });
  });

  it('collapses comments when description is collapsed', async () => {
    const user = userEvent.setup();
    api.fetchComments.mockResolvedValue([]);
    const issueWithComments = { ...mockIssue, comments: 1 };
    render(<IssueCard issue={issueWithComments} />);

    // Expand description
    const descriptionToggle = screen.getByText('Show Description (1 comment)');
    await user.click(descriptionToggle);

    // Expand comments
    await waitFor(() => {
      expect(screen.getByText(/Show Comments/i)).toBeInTheDocument();
    });
    const commentsToggle = screen.getByText(/Show Comments/i);
    await user.click(commentsToggle);

    // Collapse description - use a more flexible matcher
    const hideDescriptionToggle = screen.getByText(/Hide Description/i);
    await user.click(hideDescriptionToggle);

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
    render(<IssueCard issue={issueWithComments} />);

    // First expand description
    const descriptionToggle = screen.getByText('Show Description (1 comment)');
    await user.click(descriptionToggle);

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
});
