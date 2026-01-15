// ai-generated: Cursor
import React from 'react';
import { Tooltip } from '@patternfly/react-core';

// Map reaction content to emoji
const reactionEmojiMap = {
  '+1': '👍',
  '-1': '👎',
  laugh: '😄',
  hooray: '🎉',
  confused: '😕',
  heart: '❤️',
  rocket: '🚀',
  eyes: '👀',
};

const Reactions = ({ reactions }) => {
  if (!reactions || reactions.length === 0) {
    return null;
  }

  // Group reactions by content type
  const groupedReactions = reactions.reduce((acc, reaction) => {
    const content = reaction.content;
    if (!acc[content]) {
      acc[content] = [];
    }
    acc[content].push(reaction);
    return acc;
  }, {});

  // Get emoji for each reaction type and create tooltip content
  const reactionItems = Object.entries(groupedReactions).map(
    ([content, reactionList]) => {
      const emoji = reactionEmojiMap[content] || content;
      const count = reactionList.length;
      const users = reactionList
        .map((r) => r.user?.login || 'Unknown')
        .join(', ');

      return (
        <Tooltip key={content} content={users}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
              marginRight: '0.5rem',
              cursor: 'help',
            }}
          >
            <span style={{ fontSize: '1rem' }}>{emoji}</span>
            <span style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
              {count}
            </span>
          </span>
        </Tooltip>
      );
    }
  );

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        marginTop: '0.5rem',
      }}
    >
      {reactionItems}
    </div>
  );
};

export default Reactions;
