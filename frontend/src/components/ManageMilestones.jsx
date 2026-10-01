// Generated-by: Cursor
import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Button,
  Tooltip,
  Spinner,
  Alert,
  TextInput,
  TextArea,
  Form,
  FormGroup,
} from '@patternfly/react-core';
import {
  fetchMilestones,
  fetchMilestoneOpenCounts,
  createMilestone,
  deleteMilestone,
  updateMilestoneState,
} from '../services/api';
import milestonesCache from '../utils/milestonesCache';
import { sortMilestones } from '../utils/milestones';
import { CheckIcon, UndoIcon } from '@patternfly/react-icons';

const ManageMilestones = ({ isOpen, onClose, onMilestoneChange }) => {
  const [milestones, setMilestones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newMilestone, setNewMilestone] = useState({
    title: '',
    description: '',
    due_on: '',
  });
  const [createError, setCreateError] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [milestoneFilter, setMilestoneFilter] = useState('open');
  const [milestoneToClose, setMilestoneToClose] = useState(null);
  const [closeCounts, setCloseCounts] = useState(null);
  const [isLoadingCloseCounts, setIsLoadingCloseCounts] = useState(false);
  const [isChangingState, setIsChangingState] = useState(false);
  const [actionError, setActionError] = useState(null);
  const milestoneFilterRef = useRef('open');

  useEffect(() => {
    milestoneFilterRef.current = milestoneFilter;
    if (isOpen) loadMilestones(milestoneFilter);
  }, [isOpen, milestoneFilter]);

  // Assisted-by: openai-code-assist
  const loadMilestones = (state) => {
    // The shared cache is intentionally limited to open milestones because it
    // is also used by Planning and issue milestone selectors.
    if (state === 'open' && milestonesCache.data.length > 0) {
      setMilestones(milestonesCache.data);
      setLoading(false);
      setError(milestonesCache.error);
      // Still refresh in background
      refreshMilestonesInBackground(state);
      return;
    }

    // If data is being loaded, wait for it
    if (state === 'open' && milestonesCache.promise) {
      setLoading(true);
      milestonesCache.promise
        .then(() => {
          if (milestoneFilterRef.current === state) {
            setMilestones(milestonesCache.data);
            setLoading(false);
            setError(milestonesCache.error);
          }
        })
        .catch(() => {
          if (milestoneFilterRef.current === state) {
            setLoading(false);
            setError(milestonesCache.error);
          }
        });
      return;
    }

    // Otherwise load fresh
    setLoading(true);
    setError(null);
    fetchMilestones(state)
      .then((data) => {
        if (state === 'open') {
          milestonesCache.data = data;
          milestonesCache.loading = false;
          milestonesCache.error = null;
        }
        if (milestoneFilterRef.current === state) {
          setMilestones(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (state === 'open') {
          milestonesCache.loading = false;
          milestonesCache.error = err.message;
        }
        if (milestoneFilterRef.current === state) {
          setError(err.message);
          setLoading(false);
        }
      });
  };

  // Assisted-by: openai-code-assist
  const refreshMilestonesInBackground = (state) => {
    // Refresh in background without showing loading state
    fetchMilestones(state)
      .then((data) => {
        if (state === 'open') {
          milestonesCache.data = data;
          milestonesCache.loading = false;
          milestonesCache.error = null;
        }
        if (milestoneFilterRef.current === state) setMilestones(data);
      })
      .catch((err) => {
        if (state === 'open') {
          milestonesCache.loading = false;
          milestonesCache.error = err.message;
        }
        // Only show an error if the current view has no usable data.
        if (milestoneFilterRef.current === state && milestones.length === 0) {
          setError(err.message);
        }
      });
  };

  const formatDueDate = (dueOn) => {
    if (!dueOn) return null;
    const date = new Date(dueOn);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleDeleteMilestone = async (milestoneNumber) => {
    // Optimistically remove from UI
    const deletedMilestone = milestones.find(
      (m) => m.number === milestoneNumber
    );
    setMilestones(milestones.filter((m) => m.number !== milestoneNumber));

    // The shared cache only contains open milestones.
    if (milestoneFilter === 'open') {
      milestonesCache.data = milestonesCache.data.filter(
        (m) => m.number !== milestoneNumber
      );
    }

    try {
      await deleteMilestone(milestoneNumber);
      // Refresh in background to sync with server
      refreshMilestonesInBackground(milestoneFilter);
      if (onMilestoneChange) {
        onMilestoneChange();
      }
    } catch (err) {
      console.error('Failed to delete milestone:', err);
      // Restore on error
      if (deletedMilestone) {
        setMilestones(sortMilestones([...milestones, deletedMilestone]));
        if (milestoneFilter === 'open') {
          milestonesCache.data = sortMilestones([
            ...milestonesCache.data,
            deletedMilestone,
          ]);
        }
      }
      setError(err.message);
    }
  };

  // Assisted-by: openai-code-assist
  const handleRequestClose = async (milestone) => {
    setIsLoadingCloseCounts(true);
    setActionError(null);
    try {
      const counts = await fetchMilestoneOpenCounts(milestone.number);
      setCloseCounts(counts);
      setMilestoneToClose(milestone);
    } catch (err) {
      setActionError(`Unable to check open work: ${err.message}`);
    } finally {
      setIsLoadingCloseCounts(false);
    }
  };

  const clearCloseDialog = () => {
    setMilestoneToClose(null);
    setCloseCounts(null);
  };

  // Assisted-by: openai-code-assist
  const handleMilestoneStateChange = async (milestone, nextState) => {
    const previousMilestones = milestones;
    const previousCache = milestonesCache.data;
    setIsChangingState(true);
    setActionError(null);

    try {
      const updated = await updateMilestoneState(milestone.number, nextState);
      const updatedMilestone = {
        ...milestone,
        ...updated,
        state: nextState,
      };

      setMilestones((current) =>
        current.filter((item) => item.number !== milestone.number)
      );

      if (nextState === 'closed') {
        if (milestoneFilter === 'open') {
          milestonesCache.data = milestonesCache.data.filter(
            (item) => item.number !== milestone.number
          );
        }
        clearCloseDialog();
      } else {
        milestonesCache.data = sortMilestones([
          ...milestonesCache.data.filter(
            (item) => item.number !== milestone.number
          ),
          updatedMilestone,
        ]);
      }

      refreshMilestonesInBackground(milestoneFilter);
      onMilestoneChange?.();
    } catch (err) {
      setMilestones(previousMilestones);
      if (milestoneFilter === 'open') milestonesCache.data = previousCache;
      setActionError(`Unable to update milestone: ${err.message}`);
    } finally {
      setIsChangingState(false);
    }
  };

  const handleCreateMilestone = async () => {
    const title = String(newMilestone.title || '').trim();
    if (!title) {
      setCreateError('Title is required');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const milestoneData = {
        title: title,
      };

      const description = String(newMilestone.description || '').trim();
      if (description) {
        milestoneData.description = description;
      }

      if (newMilestone.due_on) {
        // Convert date string to ISO format
        const date = new Date(newMilestone.due_on);
        if (!isNaN(date.getTime())) {
          milestoneData.due_on = date.toISOString();
        }
      }

      const newMilestoneData = await createMilestone(milestoneData);
      // Optimistically add to UI
      setMilestones(sortMilestones([...milestones, newMilestoneData]));
      milestonesCache.data = sortMilestones([
        ...milestonesCache.data,
        newMilestoneData,
      ]);

      setIsCreateDialogOpen(false);
      setNewMilestone({ title: '', description: '', due_on: '' });
      setCreateError(null);

      // Refresh in background to sync with server
      refreshMilestonesInBackground(milestoneFilter);
      if (onMilestoneChange) {
        onMilestoneChange();
      }
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancelCreate = () => {
    setIsCreateDialogOpen(false);
    setNewMilestone({ title: '', description: '', due_on: '' });
    setCreateError(null);
  };

  return (
    <>
      <Modal
        title="Manage Milestones"
        isOpen={isOpen && !milestoneToClose}
        onClose={onClose}
        actions={[
          <Button key="close" variant="primary" onClick={onClose}>
            Close
          </Button>,
        ]}
        width="80%"
        maxWidth="800px"
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            marginBottom: '1rem',
          }}
        >
          <label htmlFor="milestone-filter">Show:</label>
          <select
            id="milestone-filter"
            aria-label="Milestone filter"
            value={milestoneFilter}
            onChange={(event) => setMilestoneFilter(event.target.value)}
          >
            <option value="open">Open milestones</option>
            <option value="closed">Closed milestones</option>
          </select>
          <Button
            variant="secondary"
            onClick={() => {
              setMilestoneFilter('open');
              setIsCreateDialogOpen(true);
            }}
            style={{
              marginLeft: 'auto',
            }}
          >
            + Create New Milestone
          </Button>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <Spinner size="lg" />
          </div>
        )}

        {error && (
          <Alert
            variant="danger"
            title="Error loading milestones"
            style={{ marginBottom: '1rem' }}
          >
            {error}
          </Alert>
        )}

        {actionError && (
          <Alert
            variant="danger"
            title="Milestone action failed"
            isInline
            style={{ marginBottom: '1rem' }}
          >
            {actionError}
          </Alert>
        )}

        {!loading && !error && (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.5rem',
              alignItems: 'center',
            }}
          >
            {milestones.length === 0 ? (
              <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                No milestones found
              </p>
            ) : (
              milestones.map((milestone) => (
                <Tooltip
                  key={milestone.number}
                  content={milestone.description || 'No description'}
                >
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.375rem 0.75rem',
                      fontSize: '0.875rem',
                      fontWeight: '500',
                      borderRadius: '0.25rem',
                      backgroundColor: '#f0f0f0',
                      border: '1px solid #d2d2d2',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <span>{milestone.title}</span>
                    {milestone.due_on && (
                      <span style={{ color: '#6a6e73', fontSize: '0.75rem' }}>
                        ({formatDueDate(milestone.due_on)})
                      </span>
                    )}
                    {milestoneFilter === 'closed' && (
                      <span
                        style={{
                          color: '#6a6e73',
                          fontSize: '0.75rem',
                          fontStyle: 'italic',
                        }}
                      >
                        Closed
                      </span>
                    )}
                    {milestone.number !== 0 && milestoneFilter === 'open' && (
                      <Tooltip content="Close milestone">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRequestClose(milestone);
                          }}
                          disabled={isLoadingCloseCounts}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#6a6e73',
                            cursor: isLoadingCloseCounts ? 'wait' : 'pointer',
                            padding: '0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '16px',
                            height: '16px',
                          }}
                          aria-label={`Close ${milestone.title} milestone`}
                        >
                          <CheckIcon />
                        </button>
                      </Tooltip>
                    )}
                    {milestone.number !== 0 && milestoneFilter === 'closed' && (
                      <Tooltip content="Reopen milestone">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleMilestoneStateChange(milestone, 'open');
                          }}
                          disabled={isChangingState}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#6a6e73',
                            cursor: isChangingState ? 'wait' : 'pointer',
                            padding: '0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: '16px',
                            height: '16px',
                          }}
                          aria-label={`Reopen ${milestone.title} milestone`}
                        >
                          <UndoIcon />
                        </button>
                      </Tooltip>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteMilestone(milestone.number);
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#6a6e73',
                        cursor: 'pointer',
                        padding: '0',
                        fontSize: '1rem',
                        lineHeight: '1',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '16px',
                        height: '16px',
                        marginLeft: '0.25rem',
                      }}
                      aria-label={`Delete ${milestone.title} milestone`}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.color = '#c9190b';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = '#6a6e73';
                      }}
                    >
                      ×
                    </button>
                  </span>
                </Tooltip>
              ))
            )}
          </div>
        )}
      </Modal>

      <Modal
        title="Create New Milestone"
        isOpen={isCreateDialogOpen}
        onClose={handleCancelCreate}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateMilestone}
            isLoading={isCreating}
            isDisabled={
              !newMilestone.title || !String(newMilestone.title).trim()
            }
          >
            Create
          </Button>,
          <Button key="cancel" variant="link" onClick={handleCancelCreate}>
            Cancel
          </Button>,
        ]}
      >
        <Form>
          <FormGroup
            label="Title"
            isRequired
            fieldId="milestone-title"
            helperTextInvalid={
              createError &&
              (!newMilestone.title || !String(newMilestone.title).trim())
                ? createError
                : ''
            }
            validated={
              createError &&
              (!newMilestone.title || !String(newMilestone.title).trim())
                ? 'error'
                : 'default'
            }
          >
            <TextInput
              id="milestone-title"
              value={newMilestone.title || ''}
              onChange={(value, event) => {
                let stringValue = '';
                if (typeof value === 'string') {
                  stringValue = value;
                } else if (
                  value &&
                  typeof value === 'object' &&
                  'target' in value
                ) {
                  stringValue = value.target?.value || '';
                } else if (event && 'target' in event) {
                  stringValue = event.target?.value || '';
                }
                setNewMilestone((prev) => ({ ...prev, title: stringValue }));
                setCreateError(null);
              }}
              placeholder="Enter milestone title"
              isRequired
            />
          </FormGroup>
          <FormGroup label="Description" fieldId="milestone-description">
            <TextArea
              id="milestone-description"
              value={newMilestone.description || ''}
              onChange={(value, event) => {
                let stringValue = '';
                if (typeof value === 'string') {
                  stringValue = value;
                } else if (
                  value &&
                  typeof value === 'object' &&
                  'target' in value
                ) {
                  stringValue = value.target?.value || '';
                } else if (event && 'target' in event) {
                  stringValue = event.target?.value || '';
                }
                setNewMilestone((prev) => ({
                  ...prev,
                  description: stringValue,
                }));
              }}
              placeholder="Enter milestone description (optional)"
              rows={4}
            />
          </FormGroup>
          <FormGroup label="Due Date" fieldId="milestone-due-on">
            <TextInput
              id="milestone-due-on"
              type="date"
              value={newMilestone.due_on || ''}
              onChange={(value, event) => {
                let stringValue = '';
                if (typeof value === 'string') {
                  stringValue = value;
                } else if (
                  value &&
                  typeof value === 'object' &&
                  'target' in value
                ) {
                  stringValue = value.target?.value || '';
                } else if (event && 'target' in event) {
                  stringValue = event.target?.value || '';
                }
                setNewMilestone((prev) => ({ ...prev, due_on: stringValue }));
              }}
            />
          </FormGroup>
          {createError &&
            newMilestone.title &&
            String(newMilestone.title).trim() && (
              <Alert variant="danger" title="Error creating milestone" isInline>
                {createError}
              </Alert>
            )}
        </Form>
      </Modal>

      {milestoneToClose && closeCounts && (
        <Modal
          title={`Close milestone: ${milestoneToClose.title}`}
          isOpen={true}
          onClose={clearCloseDialog}
          actions={[
            <Button
              key="close-milestone"
              variant="primary"
              onClick={() =>
                handleMilestoneStateChange(milestoneToClose, 'closed')
              }
              isLoading={isChangingState}
            >
              Close milestone
            </Button>,
            <Button
              key="cancel"
              variant="link"
              onClick={clearCloseDialog}
              isDisabled={isChangingState}
            >
              Cancel
            </Button>,
          ]}
        >
          {actionError && (
            <Alert variant="danger" isInline title="Unable to close milestone">
              {actionError}
            </Alert>
          )}
          {closeCounts.open_issues === 0 &&
          closeCounts.open_pull_requests === 0 ? (
            <p>There are no open issues or PRs against this milestone.</p>
          ) : (
            <p>
              There are {closeCounts.open_issues} open issue
              {closeCounts.open_issues === 1 ? '' : 's'} and{' '}
              {closeCounts.open_pull_requests} open PR
              {closeCounts.open_pull_requests === 1 ? '' : 's'} against this
              milestone.
            </p>
          )}
          <Alert variant="warning" isInline title="Open work will remain open">
            Closing this milestone will not close its issues or pull requests.
          </Alert>
        </Modal>
      )}
    </>
  );
};

export default ManageMilestones;
