// Generated-by: Cline
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import IssueTypeSelect from './IssueTypeSelect';
import * as api from '../services/api';

vi.mock('../services/api');

const featureIssue = {
  id: 1,
  number: 459,
  type: {
    name: 'Feature',
    color: 'blue',
    description: 'A request, idea, or new functionality',
  },
  child_count: 0,
  children: [],
};

describe('IssueTypeSelect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the current type icon', () => {
    render(<IssueTypeSelect issue={featureIssue} />);
    expect(screen.getByTitle('Feature')).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: /Change issue type for #459/,
      })
    ).toBeInTheDocument();
  });

  it('offers Bug, Feature, and Task with names and icons, but not Epic', async () => {
    const user = userEvent.setup();
    render(<IssueTypeSelect issue={featureIssue} />);

    await user.click(
      screen.getByRole('button', { name: /Change issue type for #459/ })
    );

    expect(
      screen.getByRole('menu', { name: 'Issue type options for #459' })
    ).toBeInTheDocument();
    for (const name of ['Bug', 'Feature', 'Task']) {
      const item = screen.getByRole('menuitem', { name });
      expect(item.querySelector('svg')).toBeInTheDocument();
    }
    expect(
      screen.queryByRole('menuitem', { name: 'Epic' })
    ).not.toBeInTheDocument();
  });

  it('updates the issue type from the menu', async () => {
    const user = userEvent.setup();
    const onChanged = vi.fn();
    api.updateIssueType.mockResolvedValue({
      type: {
        name: 'Task',
        color: 'green',
        description: 'A unit of work',
      },
    });
    render(<IssueTypeSelect issue={featureIssue} onChanged={onChanged} />);

    await user.click(
      screen.getByRole('button', { name: /Change issue type for #459/ })
    );
    await user.click(screen.getByRole('menuitem', { name: 'Task' }));

    await waitFor(() => {
      expect(api.updateIssueType).toHaveBeenCalledWith(459, 'Task');
      expect(onChanged).toHaveBeenCalledWith(
        expect.objectContaining({
          type: expect.objectContaining({ name: 'Task' }),
        })
      );
    });
  });

  it('does not call the API when the current type is selected', async () => {
    const user = userEvent.setup();
    render(<IssueTypeSelect issue={featureIssue} />);

    await user.click(
      screen.getByRole('button', { name: /Change issue type for #459/ })
    );
    await user.click(screen.getByRole('menuitem', { name: 'Feature' }));

    expect(api.updateIssueType).not.toHaveBeenCalled();
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('explains that Epic is based on sub-issues instead of opening a menu', async () => {
    const user = userEvent.setup();
    render(
      <IssueTypeSelect
        issue={{
          ...featureIssue,
          type: { name: 'Bug', color: 'red' },
          child_count: 2,
          children: [{ number: 1 }, { number: 2 }],
        }}
      />
    );

    await user.click(
      screen.getByRole('button', { name: 'Epic (based on sub-issues)' })
    );

    expect(screen.getByText('Epic is based on sub-issues')).toBeInTheDocument();
    expect(
      screen.getByText(/Epic cannot be selected directly/)
    ).toBeInTheDocument();
    expect(api.updateIssueType).not.toHaveBeenCalled();
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('menuitem', { name: 'Epic' })
    ).not.toBeInTheDocument();
  });
});
