// Assisted-by: openai-code-assist
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ManageLabels from './ManageLabels';
import * as api from '../services/api';
import { clearLabelsCache } from '../utils/labelsCache';

vi.mock('../services/api');

describe('ManageLabels editing', () => {
  const originalLabel = {
    id: 1,
    name: 'bug',
    color: 'b60205',
    description: 'Something is broken',
  };
  let fetchedLabels;

  beforeEach(() => {
    vi.clearAllMocks();
    clearLabelsCache();
    fetchedLabels = [originalLabel];
    api.fetchLabels.mockImplementation(() => Promise.resolve(fetchedLabels));
    api.updateLabel.mockImplementation(async (_labelName, labelData) => {
      fetchedLabels = [{ ...originalLabel, ...labelData }];
      return fetchedLabels[0];
    });
  });

  it('opens the edit dialog with current values and saves with OK', async () => {
    const user = userEvent.setup();
    render(<ManageLabels isOpen onClose={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('bug')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Edit bug label' }));

    expect(screen.getByText('Edit Label')).toBeInTheDocument();
    expect(screen.getByDisplayValue('bug')).toBeInTheDocument();
    expect(screen.getByDisplayValue('b60205')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Something is broken')).toBeInTheDocument();

    const nameInput = screen.getByDisplayValue('bug');
    await user.clear(nameInput);
    await user.type(nameInput, 'defect');
    await user.click(screen.getByRole('button', { name: 'OK', hidden: true }));

    await waitFor(() =>
      expect(api.updateLabel).toHaveBeenCalledWith('bug', {
        name: 'defect',
        color: 'b60205',
        description: 'Something is broken',
      })
    );
    expect(screen.getByText('defect')).toBeInTheDocument();
    expect(screen.queryByText('Edit Label')).not.toBeInTheDocument();
  });

  it('discards edits when Cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<ManageLabels isOpen onClose={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('bug')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Edit bug label' }));
    const nameInput = screen.getByDisplayValue('bug');
    await user.clear(nameInput);
    await user.type(nameInput, 'defect');
    await user.click(
      screen.getByRole('button', { name: 'Cancel', hidden: true })
    );

    expect(api.updateLabel).not.toHaveBeenCalled();
    expect(screen.getByText('bug')).toBeInTheDocument();
    expect(screen.queryByText('defect')).not.toBeInTheDocument();
  });
});
