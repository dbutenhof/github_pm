// ai-generated: Cursor
import React from 'react';
import { Button, Avatar } from '@patternfly/react-core';
import { useAuth } from '../contexts/AuthContext';

const UserProfile = () => {
  const { user, logout } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
      }}
    >
      {user.avatar_url && (
        <Avatar
          src={user.avatar_url}
          alt={user.username}
          size="md"
        />
      )}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {user.name && (
          <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
            {user.name}
          </span>
        )}
        <span style={{ fontSize: '0.75rem', color: '#6a6e73' }}>
          @{user.username}
        </span>
      </div>
      <Button variant="secondary" onClick={logout}>
        Logout
      </Button>
    </div>
  );
};

export default UserProfile;
