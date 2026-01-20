// ai-generated: Cursor
import React from 'react';

const UserAvatar = ({ user, size = 32, showName = false }) => {
  if (!user?.avatar_url) {
    return null;
  }

  const avatarImage = (
    <img
      src={user.avatar_url}
      alt={user.login || 'User'}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '50%',
        flexShrink: 0,
      }}
    />
  );

  const username = user.login || 'Unknown';

  // If showName is true, we need to return just the avatar
  // The username will be handled separately in the parent to allow proper layout
  // This maintains backward compatibility for cases where showName is false
  if (showName) {
    // Just return the linked avatar - username will be in parent
    if (user.html_url) {
      return (
        <a
          href={user.html_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ textDecoration: 'none' }}
        >
          {avatarImage}
        </a>
      );
    }
    return avatarImage;
  }

  // If showName is false, just return the avatar (for backward compatibility)
  if (user.html_url) {
    return (
      <a
        href={user.html_url}
        target="_blank"
        rel="noopener noreferrer"
        style={{ textDecoration: 'none' }}
      >
        {avatarImage}
      </a>
    );
  }

  return avatarImage;
};

export default UserAvatar;
