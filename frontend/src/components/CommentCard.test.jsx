// ai-generated: Cursor
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CommentCard from './CommentCard';

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

  it('renders comment body as HTML', () => {
    render(<CommentCard comment={mockComment} />);
    expect(screen.getByText(/Hi @sjmonson/i)).toBeInTheDocument();
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
});
