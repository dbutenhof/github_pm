// Generated-by: Cursor
import React, { useEffect } from 'react';
import { Alert } from '@patternfly/react-core';
import { usePlanningDnD } from './PlanningDnDContext';

/**
 * Scrollable planning bounds used for unlink-zone detection during issue DnD.
 *
 * Generated-by: Cursor
 */
const PlanningBoard = ({ children }) => {
  const dnd = usePlanningDnD();

  useEffect(() => {
    if (!dnd?.dragged) return undefined;

    const onDragOver = (e) => {
      e.preventDefault();
      const bounds = dnd.planningBoundsRef.current;
      if (!bounds) return;
      const rect = bounds.getBoundingClientRect();
      const inside =
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom;
      dnd.pointerOverPlanning(inside);
    };

    window.addEventListener('dragover', onDragOver);
    return () => window.removeEventListener('dragover', onDragOver);
  }, [dnd]);

  return (
    <div
      ref={dnd?.planningBoundsRef}
      data-testid="planning-board"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        minHeight: '12rem',
      }}
    >
      {dnd?.error && (
        <Alert variant="danger" title="Hierarchy update failed" isInline>
          {dnd.error}
        </Alert>
      )}
      {children}
    </div>
  );
};

export default PlanningBoard;
