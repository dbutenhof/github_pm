// Generated-by: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { PlanningDnDProvider, usePlanningDnD } from './PlanningDnDContext';
import * as api from '../services/api';

vi.mock('../services/api');

const Probe = ({ issue }) => {
  const dnd = usePlanningDnD();
  return (
    <div>
      <button
        type="button"
        draggable
        onDragStart={(e) =>
          dnd.beginDrag(e, {
            issue,
            sourceMilestoneNumber: 1,
            descendantNumbers: new Set([issue.number]),
          })
        }
        onDragEnd={() => dnd.finishDrag()}
      >
        drag-me
      </button>
      <button
        type="button"
        onClick={() =>
          dnd.pointerOverParent({ number: 10, title: 'Parent' }, 2)
        }
      >
        drop-target
      </button>
      <span data-testid="unlink">{dnd.isUnlinkZone ? 'unlink' : 'link'}</span>
      <button type="button" onClick={() => dnd.pointerOverPlanning(false)}>
        leave-bounds
      </button>
    </div>
  );
};

const makeDataTransfer = () => ({
  effectAllowed: 'move',
  setData: vi.fn(),
  setDragImage: vi.fn(),
});

describe('PlanningDnDContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.setIssueParent.mockResolvedValue({
      from_milestone: 1,
      to_milestone: 2,
      updated_issue_numbers: [5],
    });
    api.clearIssueParent.mockResolvedValue({ parent_number: 9 });
  });

  it('relinks on drop over a parent', async () => {
    const onHierarchyChanged = vi.fn();
    const issue = { number: 5, parent_number: null };

    await act(async () => {
      render(
        <PlanningDnDProvider
          milestones={[
            { number: 1, title: 'M1' },
            { number: 2, title: 'M2' },
          ]}
          onHierarchyChanged={onHierarchyChanged}
        >
          <Probe issue={issue} />
        </PlanningDnDProvider>
      );
    });

    const dragBtn = screen.getByText('drag-me');

    await act(async () => {
      const start = new Event('dragstart', { bubbles: true });
      Object.defineProperty(start, 'dataTransfer', {
        value: makeDataTransfer(),
      });
      dragBtn.dispatchEvent(start);
    });

    await act(async () => {
      screen.getByText('drop-target').click();
    });

    await act(async () => {
      dragBtn.dispatchEvent(new Event('dragend', { bubbles: true }));
    });

    await waitFor(() => {
      expect(api.setIssueParent).toHaveBeenCalledWith(5, 10);
      expect(onHierarchyChanged).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'relink',
          parentNumber: 10,
          targetMilestoneNumber: 2,
        })
      );
    });
  });

  it('unlinks when released in unlink zone', async () => {
    const onHierarchyChanged = vi.fn();
    const issue = { number: 5, parent_number: 9 };

    await act(async () => {
      render(
        <PlanningDnDProvider
          milestones={[{ number: 1, title: 'M1' }]}
          onHierarchyChanged={onHierarchyChanged}
        >
          <Probe issue={issue} />
        </PlanningDnDProvider>
      );
    });

    const dragBtn = screen.getByText('drag-me');

    await act(async () => {
      const start = new Event('dragstart', { bubbles: true });
      Object.defineProperty(start, 'dataTransfer', {
        value: makeDataTransfer(),
      });
      dragBtn.dispatchEvent(start);
    });

    await act(async () => {
      screen.getByText('leave-bounds').click();
    });
    expect(screen.getByTestId('unlink').textContent).toBe('unlink');

    await act(async () => {
      dragBtn.dispatchEvent(new Event('dragend', { bubbles: true }));
    });

    await waitFor(() => {
      expect(api.clearIssueParent).toHaveBeenCalledWith(5);
      expect(onHierarchyChanged).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'unlink', issueNumber: 5 })
      );
    });
  });
});
