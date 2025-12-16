import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getDaysSince, formatDate } from '../utils/dateUtils';

const CommentCard = ({ comment }) => {
  const daysSince = getDaysSince(comment.created_at);

  return (
    <div
      style={{
        marginTop: '1rem',
        paddingTop: '1rem',
        borderTop: '1px solid #d2d2d2',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.5rem',
          marginBottom: '0.75rem',
        }}
      >
        {comment.user?.avatar_url && (
          <img
            src={comment.user.avatar_url}
            alt={comment.user.login}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              flexShrink: 0,
            }}
          />
        )}
        <div style={{ flex: '1', minWidth: 0 }}>
          <div style={{ fontWeight: '500' }}>
            {comment.user?.login || 'Unknown'}
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
            {formatDate(comment.created_at)} ({daysSince} days ago)
          </div>
        </div>
      </div>
      <div>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {comment.body}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default CommentCard;
