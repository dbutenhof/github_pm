import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MilestoneCard from './MilestoneCard';
import * as api from '../services/api';

vi.mock('../services/api');

describe('MilestoneCard', () => {
  const mockMilestone = {
    number: 6,
    title: 'v0.6.0',
    description: 'Version 0.6.0',
    due_on: '2025-12-31T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchLabels.mockResolvedValue([]);
  });

  it('renders milestone title', () => {
    render(<MilestoneCard milestone={mockMilestone} />);
    expect(screen.getByText('v0.6.0')).toBeInTheDocument();
  });

  it('renders milestone description when provided', () => {
    render(<MilestoneCard milestone={mockMilestone} />);
    expect(screen.getByText('Version 0.6.0')).toBeInTheDocument();
  });

  it('renders due date when provided', () => {
    render(<MilestoneCard milestone={mockMilestone} />);
    expect(screen.getByText(/Due:/i)).toBeInTheDocument();
  });

  it('expands and fetches issues when clicked', async () => {
    const user = userEvent.setup();
    const mockIssues = [
      {
        id: 1,
        number: 459,
        title: 'Test Issue',
        body: 'Issue body',
        html_url: 'https://github.com/test/issue/459',
        user: { login: 'testuser', avatar_url: 'https://avatar.url' },
        created_at: '2025-01-01T00:00:00Z',
      },
    ];
    api.fetchIssues.mockResolvedValue(mockIssues);

    render(<MilestoneCard milestone={mockMilestone} />);
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(api.fetchIssues).toHaveBeenCalledWith(6);
    });

    await waitFor(() => {
      expect(screen.getByText(/Test Issue/)).toBeInTheDocument();
    });
  });

  it('shows loading spinner while fetching issues', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockImplementation(() => new Promise(() => {}));

    render(<MilestoneCard milestone={mockMilestone} />);
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockRejectedValue(new Error('Fetch failed'));

    render(<MilestoneCard milestone={mockMilestone} />);
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText(/Error loading issues/i)).toBeInTheDocument();
    });
  });

  it('shows empty message when no issues', async () => {
    const user = userEvent.setup();
    api.fetchIssues.mockResolvedValue([]);

    render(<MilestoneCard milestone={mockMilestone} />);
    const expandButton = screen.getByRole('button', { name: /show issues/i });
    await user.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText(/No issues found/i)).toBeInTheDocument();
    });
  });
});
