// Generated-by: Cursor
// Assisted-by: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CommentCard from './CommentCard';
import * as api from '../services/api';

vi.mock('../services/api');

describe('CommentCard', () => {
  const mockComment = {
    id: 3148506196,
    body: 'Hi @sjmonson, thanks for opening this!',
    body_html: '<p>Hi @sjmonson, thanks for opening this!</p>',
    user: {
      login: 'MaxMarriottClarke',
      avatar_url: 'https://avatars.githubusercontent.com/u/108399722?v=4',
    },
    created_at: '2025-08-03T15:47:13Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders comment body as HTML', () => {
    const { container } = render(<CommentCard comment={mockComment} />);
    expect(screen.getByText(/Hi @sjmonson/i)).toBeInTheDocument();
    expect(container.querySelector('.markdown-body')).toBeInTheDocument();
  });

  it('keeps list and heading markup inside markdown-body', () => {
    const commentWithStructure = {
      ...mockComment,
      body_html:
        '<h2>Notes</h2><ul><li>First item</li><li>Second item</li></ul>',
    };
    const { container } = render(
      <CommentCard comment={commentWithStructure} />
    );
    const markdown = container.querySelector('.markdown-body');
    expect(markdown.querySelector('h2')).toHaveTextContent('Notes');
    expect(markdown.querySelectorAll('ul li')).toHaveLength(2);
  });

  it('renders user information', () => {
    render(<CommentCard comment={mockComment} />);
    expect(screen.getByText('MaxMarriottClarke')).toBeInTheDocument();
  });

  it('renders user avatar', () => {
    render(<CommentCard comment={mockComment} />);
    const avatar = screen.getByAltText('MaxMarriottClarke');
    expect(avatar).toHaveAttribute('src', mockComment.user.avatar_url);
  });

  it('renders created date with days since', () => {
    render(<CommentCard comment={mockComment} />);
    expect(screen.getByText(/\(/)).toBeInTheDocument(); // Should contain days ago
  });

  it('handles missing user gracefully', () => {
    const commentWithoutUser = { ...mockComment, user: null };
    render(<CommentCard comment={commentWithoutUser} />);
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  it('shows edit icon and opens markdown editor with current body', async () => {
    const user = userEvent.setup();
    render(<CommentCard comment={mockComment} />);

    await user.click(screen.getByRole('button', { name: 'Edit comment' }));
    expect(screen.getByText('Edit comment')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Write markdown…')).toHaveValue(
      mockComment.body
    );
    expect(screen.getByRole('button', { name: 'OK' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();
  });

  it('updates comment on OK and notifies parent', async () => {
    const user = userEvent.setup();
    const onCommentUpdated = vi.fn();
    const updated = {
      ...mockComment,
      body: 'Updated body',
      body_html: '<p>Updated body</p>',
    };
    api.updateComment.mockResolvedValue(updated);

    render(
      <CommentCard comment={mockComment} onCommentUpdated={onCommentUpdated} />
    );

    await user.click(screen.getByRole('button', { name: 'Edit comment' }));
    const textarea = screen.getByPlaceholderText('Write markdown…');
    await user.clear(textarea);
    await user.type(textarea, 'Updated body');
    await user.click(screen.getByRole('button', { name: 'OK' }));

    await waitFor(() => {
      expect(api.updateComment).toHaveBeenCalledWith(
        mockComment.id,
        'Updated body'
      );
      expect(onCommentUpdated).toHaveBeenCalledWith(updated);
      expect(screen.getByText('Updated body')).toBeInTheDocument();
    });
  });
});
