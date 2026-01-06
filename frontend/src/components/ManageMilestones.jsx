// ai-generated: Cursor
import React, { useState, useEffect } from 'react';
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
  createMilestone,
  deleteMilestone,
} from '../services/api';
import milestonesCache from '../utils/milestonesCache';

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

  useEffect(() => {
    if (isOpen) {
      loadMilestones();
    }
  }, [isOpen]);

  const loadMilestones = () => {
    // Use cached data if available
    if (milestonesCache.data.length > 0) {
      setMilestones(milestonesCache.data);
      setLoading(false);
      setError(milestonesCache.error);
      // Still refresh in background
      refreshMilestonesInBackground();
      return;
    }

    // If data is being loaded, wait for it
    if (milestonesCache.promise) {
      setLoading(true);
      milestonesCache.promise
        .then(() => {
          setMilestones(milestonesCache.data);
          setLoading(false);
          setError(milestonesCache.error);
        })
        .catch(() => {
          setLoading(false);
          setError(milestonesCache.error);
        });
      return;
    }

    // Otherwise load fresh
    setLoading(true);
    setError(null);
    fetchMilestones()
      .then((data) => {
        milestonesCache.data = data;
        milestonesCache.loading = false;
        milestonesCache.error = null;
        setMilestones(data);
        setLoading(false);
      })
      .catch((err) => {
        milestonesCache.loading = false;
        milestonesCache.error = err.message;
        setError(err.message);
        setLoading(false);
      });
  };

  const refreshMilestonesInBackground = () => {
    // Refresh in background without showing loading state
    fetchMilestones()
      .then((data) => {
        milestonesCache.data = data;
        milestonesCache.loading = false;
        milestonesCache.error = null;
        setMilestones(data);
      })
      .catch((err) => {
        milestonesCache.loading = false;
        milestonesCache.error = err.message;
        // Only show error if we don't have cached data
        if (milestones.length === 0) {
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

    // Also remove from cache
    milestonesCache.data = milestonesCache.data.filter(
      (m) => m.number !== milestoneNumber
    );

    try {
      await deleteMilestone(milestoneNumber);
      // Refresh in background to sync with server
      refreshMilestonesInBackground();
      if (onMilestoneChange) {
        onMilestoneChange();
      }
    } catch (err) {
      console.error('Failed to delete milestone:', err);
      // Restore on error
      if (deletedMilestone) {
        setMilestones(
          [...milestones, deletedMilestone].sort((a, b) => a.number - b.number)
        );
        milestonesCache.data = [...milestonesCache.data, deletedMilestone].sort(
          (a, b) => a.number - b.number
        );
      }
      setError(err.message);
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
      setMilestones(
        [...milestones, newMilestoneData].sort((a, b) => a.number - b.number)
      );
      milestonesCache.data = [...milestonesCache.data, newMilestoneData].sort(
        (a, b) => a.number - b.number
      );

      setIsCreateDialogOpen(false);
      setNewMilestone({ title: '', description: '', due_on: '' });
      setCreateError(null);

      // Refresh in background to sync with server
      refreshMilestonesInBackground();
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
        isOpen={isOpen}
        onClose={onClose}
        actions={[
          <Button key="close" variant="primary" onClick={onClose}>
            Close
          </Button>,
        ]}
        width="80%"
        maxWidth="800px"
      >
        <div style={{ marginBottom: '1rem' }}>
          <Button
            variant="secondary"
            onClick={() => setIsCreateDialogOpen(true)}
            style={{
              marginBottom: '1rem',
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
    </>
  );
};

export default ManageMilestones;
