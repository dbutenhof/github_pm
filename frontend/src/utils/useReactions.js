// Generated-by: Codex
import { useEffect, useState } from 'react';

// A failed or empty result completes an attempt. Only the resource, its server
// summary, or opening the description again can start another attempt.
export const useReactions = (id, count, active, loader, initial) => {
  const [state, setState] = useState({
    data: initial || [],
    loading: false,
    error: null,
  });
  useEffect(() => {
    let current = true;
    if (initial !== undefined) {
      setState({ data: initial, loading: false, error: null });
    } else if (active && count > 0) {
      setState({ data: [], loading: true, error: null });
      loader(id).then(
        (data) => {
          if (current) setState({ data, loading: false, error: null });
        },
        (error) => {
          if (current)
            setState({ data: [], loading: false, error: error.message });
        }
      );
    } else {
      setState({ data: [], loading: false, error: null });
    }
    return () => {
      current = false;
    };
  }, [id, count, active, loader, initial]);
  return state;
};
