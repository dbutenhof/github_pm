// Generated-by: openai-code-assist
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ManageMilestones from './ManageMilestones';
import * as api from '../services/api';
import { clearMilestonesCache } from '../utils/milestonesCache';

vi.mock('../services/api');

describe('ManageMilestones state actions', () => {
  const openMilestone = {
    number: 6,
    title: 'v0.6.0',
    description: 'Version 0.6.0',
    due_on: null,
    state: 'open',
  };
  const closedMilestone = { ...openMilestone, state: 'closed' };
  let openResults;
  let closedResults;

  beforeEach(() => {
    vi.clearAllMocks();
    clearMilestonesCache();
    openResults = [openMilestone];
    closedResults = [closedMilestone];
    api.fetchMilestones.mockImplementation((state = 'open') =>
      Promise.resolve(state === 'closed' ? closedResults : openResults)
    );
    api.fetchMilestoneOpenCounts.mockResolvedValue({
      open_issues: 2,
      open_pull_requests: 1,
    });
    api.updateMilestoneState.mockResolvedValue({
      ...closedMilestone,
    });
  });

  it('confirms close with open issue and pull-request counts', async () => {
    const user = userEvent.setup();
    render(
      <ManageMilestones isOpen onClose={vi.fn()} onMilestoneChange={vi.fn()} />
    );

    await waitFor(() => expect(screen.getByText('v0.6.0')).toBeInTheDocument());
    await user.click(
      screen.getByRole('button', { name: 'Close v0.6.0 milestone' })
    );

    await waitFor(() => {
      expect(api.fetchMilestoneOpenCounts).toHaveBeenCalledWith(6);
      expect(
        screen.getByText(
          'There are 2 open issues and 1 open PR against this milestone.'
        )
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/will not close its issues or pull requests/i)
    ).toBeInTheDocument();
    openResults = [];
    await user.click(screen.getByRole('button', { name: 'Close milestone' }));

    await waitFor(() => {
      expect(api.updateMilestoneState).toHaveBeenCalledWith(6, 'closed');
      expect(screen.queryByText('v0.6.0')).not.toBeInTheDocument();
    });
  });

  it('loads closed milestones and can reopen one', async () => {
    const user = userEvent.setup();
    render(
      <ManageMilestones isOpen onClose={vi.fn()} onMilestoneChange={vi.fn()} />
    );

    await waitFor(() => expect(screen.getByText('v0.6.0')).toBeInTheDocument());
    await user.selectOptions(
      screen.getByLabelText('Milestone filter'),
      'closed'
    );

    await waitFor(() => {
      expect(api.fetchMilestones).toHaveBeenCalledWith('closed');
      expect(screen.getByText('Closed')).toBeInTheDocument();
    });
    closedResults = [];
    await user.click(
      screen.getByRole('button', { name: 'Reopen v0.6.0 milestone' })
    );

    await waitFor(() => {
      expect(api.updateMilestoneState).toHaveBeenCalledWith(6, 'open');
      expect(screen.queryByText('v0.6.0')).not.toBeInTheDocument();
    });
  });
});
