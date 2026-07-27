// Generated-by: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MarkdownInputModal from './MarkdownInputModal';
import * as api from '../services/api';

vi.mock('../services/api');

describe('MarkdownInputModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.renderMarkdown.mockResolvedValue({
      html: '<p><strong>hi</strong></p>',
    });
    api.fetchLabels.mockResolvedValue([
      { id: 1, name: 'bug', color: 'ff0000', description: 'A bug' },
    ]);
    api.fetchAssignees.mockResolvedValue([
      { login: 'alice', avatar_url: 'https://example.com/a.png' },
    ]);
  });

  it('renders comment modal with edit tab and submit/cancel', async () => {
    const onClose = vi.fn();
    render(
      <MarkdownInputModal
        isOpen
        onClose={onClose}
        mode="comment"
        title="Add Comment"
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByText('Add Comment')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();
  });

  it('shows Close with Comment when enabled', () => {
    render(
      <MarkdownInputModal
        isOpen
        onClose={vi.fn()}
        mode="comment"
        showCloseWithComment
        onSubmit={vi.fn()}
        onCloseWithComment={vi.fn()}
      />
    );
    expect(
      screen.getByRole('button', { name: 'Close with Comment' })
    ).toBeInTheDocument();
  });

  it('submits comment body', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(
      <MarkdownInputModal
        isOpen
        onClose={onClose}
        mode="comment"
        onSubmit={onSubmit}
      />
    );

    await user.type(screen.getByPlaceholderText('Write markdown…'), 'Hello');
    await user.click(screen.getByRole('button', { name: 'Submit' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith('Hello');
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('loads preview via renderMarkdown when Preview tab selected', async () => {
    const user = userEvent.setup();
    render(
      <MarkdownInputModal
        isOpen
        onClose={vi.fn()}
        mode="comment"
        onSubmit={vi.fn()}
      />
    );

    await user.type(screen.getByPlaceholderText('Write markdown…'), '**hi**');
    await user.click(screen.getByText('Preview'));

    await waitFor(() => {
      expect(api.renderMarkdown).toHaveBeenCalledWith('**hi**');
    });
    await waitFor(() => {
      expect(screen.getByText('hi')).toBeInTheDocument();
      // Modal content is portaled to document.body, not the RTL container
      expect(document.querySelector('.markdown-body')).toBeInTheDocument();
    });
  });

  it('renders issue mode fields and submits payload', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <MarkdownInputModal
        isOpen
        onClose={vi.fn()}
        mode="issue"
        title="Add Issue"
        submitLabel="Create Issue"
        onSubmit={onSubmit}
      />
    );

    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bug' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Feature' })).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText('Issue title'), 'My epic');
    await user.click(screen.getByRole('button', { name: 'Bug' }));
    await user.type(screen.getByPlaceholderText('Write markdown…'), 'Details');
    await user.click(screen.getByRole('button', { name: 'Create Issue' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'My epic',
          body: 'Details',
          type: 'Bug',
        })
      );
    });
  });

  it('calls onClose when Cancel is clicked', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <MarkdownInputModal
        isOpen
        onClose={onClose}
        mode="comment"
        onSubmit={vi.fn()}
      />
    );
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalled();
  });
});
