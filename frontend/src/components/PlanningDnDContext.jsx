// Generated-by: Cursor
import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';
import { clearIssueParent, setIssueParent } from '../services/api';

const PlanningDnDContext = createContext(null);

export const usePlanningDnD = () => useContext(PlanningDnDContext);

/**
 * Coordinates cross-milestone issue parent drag/relink/unlink for Planning.
 *
 * Generated-by: Cursor
 */
export const PlanningDnDProvider = ({
  children,
  onHierarchyChanged,
  milestones = [],
}) => {
  const planningBoundsRef = useRef(null);
  const dragImageRef = useRef(null);
  const draggedRef = useRef(null);
  const hoverParentRef = useRef(null);
  const isUnlinkZoneRef = useRef(false);
  const onHierarchyChangedRef = useRef(onHierarchyChanged);
  onHierarchyChangedRef.current = onHierarchyChanged;

  const [dragged, setDragged] = useState(null);
  const [hoverParent, setHoverParentState] = useState(null);
  const [isUnlinkZone, setIsUnlinkZoneState] = useState(false);
  const [error, setError] = useState(null);

  const setHoverParent = useCallback((value) => {
    hoverParentRef.current = value;
    setHoverParentState(value);
  }, []);

  const setIsUnlinkZone = useCallback((value) => {
    isUnlinkZoneRef.current = value;
    setIsUnlinkZoneState(value);
  }, []);

  const milestoneTitle = useCallback(
    (number) => {
      const m = milestones.find((x) => x.number === number);
      return m?.title || (number === 0 ? 'none' : `#${number}`);
    },
    [milestones]
  );

  const updateDragImage = useCallback((issueNumber, opts = {}) => {
    const el = dragImageRef.current;
    if (!el) return;
    const { parentLabel, milestoneLabel, unlink } = opts;
    if (unlink) {
      el.textContent = `#${issueNumber} → Unlink (become Epic)`;
      el.style.backgroundColor = '#f0ab00';
      el.style.color = '#1b1d21';
      return;
    }
    const parentPart = parentLabel
      ? ` under ${parentLabel}`
      : ' (pick a parent)';
    const msPart = milestoneLabel ? ` · milestone: ${milestoneLabel}` : '';
    el.textContent = `#${issueNumber}${parentPart}${msPart}`;
    el.style.backgroundColor = '#0066cc';
    el.style.color = '#fff';
  }, []);

  const beginDrag = useCallback(
    (e, payload) => {
      setError(null);
      draggedRef.current = payload;
      setDragged(payload);
      setHoverParent(null);
      setIsUnlinkZone(false);
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData(
        'application/x-guidellm-issue',
        String(payload.issue.number)
      );
      e.dataTransfer.setData('text/plain', String(payload.issue.number));

      if (!dragImageRef.current) {
        const el = document.createElement('div');
        el.style.position = 'absolute';
        el.style.top = '-1000px';
        el.style.left = '-1000px';
        el.style.padding = '0.35rem 0.75rem';
        el.style.borderRadius = '0.25rem';
        el.style.fontSize = '0.875rem';
        el.style.fontWeight = '600';
        el.style.pointerEvents = 'none';
        el.style.whiteSpace = 'nowrap';
        el.style.zIndex = '10000';
        document.body.appendChild(el);
        dragImageRef.current = el;
      }
      updateDragImage(payload.issue.number, {});
      e.dataTransfer.setDragImage(dragImageRef.current, 12, 12);
    },
    [setHoverParent, setIsUnlinkZone, updateDragImage]
  );

  const pointerOverParent = useCallback(
    (parentIssue, parentMilestoneNumber) => {
      const current = draggedRef.current;
      if (!current) return;
      if (parentIssue.number === current.issue.number) return;
      if (current.descendantNumbers?.has(parentIssue.number)) return;
      setIsUnlinkZone(false);
      setHoverParent({
        issue: parentIssue,
        milestoneNumber: parentMilestoneNumber,
      });
      updateDragImage(current.issue.number, {
        parentLabel: `#${parentIssue.number}`,
        milestoneLabel: milestoneTitle(parentMilestoneNumber),
      });
    },
    [milestoneTitle, setHoverParent, setIsUnlinkZone, updateDragImage]
  );

  const pointerOverPlanning = useCallback(
    (inside) => {
      const current = draggedRef.current;
      if (!current) return;
      if (!inside) {
        setIsUnlinkZone(true);
        setHoverParent(null);
        updateDragImage(current.issue.number, { unlink: true });
      } else if (isUnlinkZoneRef.current && !hoverParentRef.current) {
        setIsUnlinkZone(false);
        updateDragImage(current.issue.number, {});
      }
    },
    [setHoverParent, setIsUnlinkZone, updateDragImage]
  );

  const finishDrag = useCallback(async () => {
    const current = draggedRef.current;
    const parent = hoverParentRef.current;
    const unlink = isUnlinkZoneRef.current;

    draggedRef.current = null;
    hoverParentRef.current = null;
    isUnlinkZoneRef.current = false;
    setDragged(null);
    setHoverParentState(null);
    setIsUnlinkZoneState(false);

    if (!current) return;

    try {
      if (unlink) {
        if (
          current.issue.parent_number == null &&
          !current.issue.external_parent
        ) {
          return;
        }
        await clearIssueParent(current.issue.number);
        onHierarchyChangedRef.current?.({
          type: 'unlink',
          issueNumber: current.issue.number,
          issueSnapshot: current.issue,
          sourceMilestoneNumber: current.sourceMilestoneNumber,
        });
        return;
      }

      if (parent) {
        const result = await setIssueParent(
          current.issue.number,
          parent.issue.number
        );
        onHierarchyChangedRef.current?.({
          type: 'relink',
          issueNumber: current.issue.number,
          issueSnapshot: current.issue,
          parentNumber: parent.issue.number,
          sourceMilestoneNumber: current.sourceMilestoneNumber,
          targetMilestoneNumber: parent.milestoneNumber,
          fromMilestone: result.from_milestone,
          toMilestone: result.to_milestone,
          updatedIssueNumbers: result.updated_issue_numbers || [],
        });
      }
    } catch (err) {
      setError(err.message || String(err));
      onHierarchyChangedRef.current?.({
        type: 'error',
        message: err.message || String(err),
        sourceMilestoneNumber: current.sourceMilestoneNumber,
        targetMilestoneNumber: parent?.milestoneNumber,
      });
    }
  }, []);

  const value = useMemo(
    () => ({
      planningBoundsRef,
      dragged,
      hoverParent,
      isUnlinkZone,
      error,
      clearError: () => setError(null),
      beginDrag,
      pointerOverParent,
      pointerOverPlanning,
      finishDrag,
      setHoverParent,
    }),
    [
      dragged,
      hoverParent,
      isUnlinkZone,
      error,
      beginDrag,
      pointerOverParent,
      pointerOverPlanning,
      finishDrag,
      setHoverParent,
    ]
  );

  return (
    <PlanningDnDContext.Provider value={value}>
      {children}
    </PlanningDnDContext.Provider>
  );
};
