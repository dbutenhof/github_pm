// ai-generated: Cursor
import React, { useState, useEffect } from 'react';
import { Spinner, Alert } from '@patternfly/react-core';
import { getDaysSince, formatDate } from '../utils/dateUtils';
import { fetchCommentReactions } from '../services/api';
import Reactions from './Reactions';
import UserAvatar from './UserAvatar';

const CommentCard = ({ comment }) => {
  const daysSince = getDaysSince(comment.created_at);
  const [reactions, setReactions] = useState([]);
  const [reactionsLoading, setReactionsLoading] = useState(false);
  const [reactionsError, setReactionsError] = useState(null);

  // Reset reactions when comment changes
  useEffect(() => {
    if (comment.id) {
      setReactions([]);
      setReactionsError(null);
    }
  }, [comment.id]);

  // Fetch reactions if total_count > 0
  useEffect(() => {
    if (
      comment.reactions?.total_count > 0 &&
      reactions.length === 0 &&
      !reactionsLoading
    ) {
      setReactionsLoading(true);
      setReactionsError(null);
      fetchCommentReactions(comment.id)
        .then((data) => {
          setReactions(data);
          setReactionsLoading(false);
        })
        .catch((err) => {
          setReactionsError(err.message);
          setReactionsLoading(false);
        });
    }
  }, [
    comment.reactions?.total_count,
    comment.id,
    reactions.length,
    reactionsLoading,
  ]);

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
          flexDirection: 'column',
          alignItems: 'flex-start',
          marginBottom: '0.75rem',
        }}
      >
        {comment.user?.html_url ? (
          <a
            href={comment.user.html_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <UserAvatar user={comment.user} size={32} />
            <div style={{ fontWeight: '500', color: '#0066cc' }}>
              {comment.user.login || 'Unknown'}
            </div>
          </a>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <UserAvatar user={comment.user} size={32} />
            <div style={{ fontWeight: '500' }}>
              {comment.user?.login || 'Unknown'}
            </div>
          </div>
        )}
        <div
          style={{ fontSize: '0.875rem', color: '#6a6e73', marginLeft: '40px' }}
        >
          {formatDate(comment.created_at)} ({daysSince} days ago)
        </div>
      </div>
      <div dangerouslySetInnerHTML={{ __html: comment.body_html || '' }} />
      {comment.reactions?.total_count > 0 && (
        <div style={{ marginTop: '0.5rem' }}>
          {reactionsLoading && (
            <div style={{ textAlign: 'center', padding: '0.5rem' }}>
              <Spinner size="sm" />
            </div>
          )}
          {reactionsError && (
            <Alert variant="danger" title="Error loading reactions" isInline>
              {reactionsError}
            </Alert>
          )}
          {!reactionsLoading && !reactionsError && reactions.length > 0 && (
            <Reactions reactions={reactions} />
          )}
        </div>
      )}
    </div>
  );
};

export default CommentCard;
