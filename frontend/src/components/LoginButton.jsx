// ai-generated: Cursor
import React from 'react';
import { Button } from '@patternfly/react-core';
import { useAuth } from '../contexts/AuthContext';

const LoginButton = () => {
  const { login } = useAuth();

  return (
    <Button variant="primary" onClick={login}>
      Login with GitHub
    </Button>
  );
};

export default LoginButton;
