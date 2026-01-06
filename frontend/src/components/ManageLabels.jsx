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
import { fetchLabels, createLabel, deleteLabel } from '../services/api';
import labelsCache, { clearLabelsCache } from '../utils/labelsCache';

const ManageLabels = ({ isOpen, onClose, onLabelChange }) => {
  const [labels, setLabels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newLabel, setNewLabel] = useState({
    name: '',
    color: '',
    description: '',
  });
  const [createError, setCreateError] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadLabels();
    }
  }, [isOpen]);

  const loadLabels = () => {
    // Use cached data if available
    if (labelsCache.data.length > 0) {
      setLabels(labelsCache.data);
      setLoading(false);
      setError(labelsCache.error);
      // Still refresh in background
      refreshLabelsInBackground();
      return;
    }

    // If data is being loaded, wait for it
    if (labelsCache.promise) {
      setLoading(true);
      labelsCache.promise
        .then(() => {
          setLabels(labelsCache.data);
          setLoading(false);
          setError(labelsCache.error);
        })
        .catch(() => {
          setLoading(false);
          setError(labelsCache.error);
        });
      return;
    }

    // Otherwise load fresh
    setLoading(true);
    setError(null);
    fetchLabels()
      .then((data) => {
        labelsCache.data = data;
        labelsCache.loading = false;
        labelsCache.error = null;
        setLabels(data);
        setLoading(false);
      })
      .catch((err) => {
        labelsCache.loading = false;
        labelsCache.error = err.message;
        setError(err.message);
        setLoading(false);
      });
  };

  const refreshLabelsInBackground = () => {
    // Refresh in background without showing loading state
    fetchLabels()
      .then((data) => {
        labelsCache.data = data;
        labelsCache.loading = false;
        labelsCache.error = null;
        setLabels(data);
      })
      .catch((err) => {
        labelsCache.loading = false;
        labelsCache.error = err.message;
        // Only show error if we don't have cached data
        if (labels.length === 0) {
          setError(err.message);
        }
      });
  };

  const handleDeleteLabel = async (labelName) => {
    // Optimistically remove from UI
    const deletedLabel = labels.find((l) => l.name === labelName);
    setLabels(labels.filter((l) => l.name !== labelName));

    // Also remove from cache
    labelsCache.data = labelsCache.data.filter((l) => l.name !== labelName);

    try {
      await deleteLabel(labelName);
      // Refresh in background to sync with server
      refreshLabelsInBackground();
      if (onLabelChange) {
        onLabelChange();
      }
    } catch (err) {
      console.error('Failed to delete label:', err);
      // Restore on error
      if (deletedLabel) {
        setLabels(
          [...labels, deletedLabel].sort((a, b) => a.name.localeCompare(b.name))
        );
        labelsCache.data = [...labelsCache.data, deletedLabel].sort((a, b) =>
          a.name.localeCompare(b.name)
        );
      }
      setError(err.message);
    }
  };

  const handleCreateLabel = async () => {
    const name = String(newLabel.name || '').trim();
    if (!name) {
      setCreateError('Name is required');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const labelData = {
        name: name,
      };

      const color = String(newLabel.color || '').trim();
      if (color) {
        // Remove # if present
        labelData.color = color.replace(/^#/, '');
      }

      const description = String(newLabel.description || '').trim();
      if (description) {
        labelData.description = description;
      }

      const newLabelData = await createLabel(labelData);
      // Optimistically add to UI
      setLabels(
        [...labels, newLabelData].sort((a, b) => a.name.localeCompare(b.name))
      );
      labelsCache.data = [...labelsCache.data, newLabelData].sort((a, b) =>
        a.name.localeCompare(b.name)
      );

      setIsCreateDialogOpen(false);
      setNewLabel({ name: '', color: '', description: '' });
      setCreateError(null);

      // Refresh in background to sync with server
      refreshLabelsInBackground();
      if (onLabelChange) {
        onLabelChange();
      }
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancelCreate = () => {
    setIsCreateDialogOpen(false);
    setNewLabel({ name: '', color: '', description: '' });
    setCreateError(null);
  };

  const getContrastColor = (hexColor) => {
    if (!hexColor) return '#000000';
    // Remove # if present
    const color = hexColor.replace('#', '');
    const r = parseInt(color.substring(0, 2), 16);
    const g = parseInt(color.substring(2, 4), 16);
    const b = parseInt(color.substring(4, 6), 16);
    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#000000' : '#ffffff';
  };

  return (
    <>
      <Modal
        title="Manage Labels"
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
            + Create New Label
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
            title="Error loading labels"
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
            {labels.length === 0 ? (
              <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                No labels found
              </p>
            ) : (
              labels.map((label) => (
                <Tooltip
                  key={label.id || label.name}
                  content={label.description || 'No description'}
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
                      backgroundColor: `#${label.color || 'f0f0f0'}`,
                      color: getContrastColor(label.color),
                      border: '1px solid #d2d2d2',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <span>{label.name}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteLabel(label.name);
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: getContrastColor(label.color),
                        cursor: 'pointer',
                        padding: '0',
                        fontSize: '0.875rem',
                        lineHeight: '1',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '16px',
                        height: '16px',
                        marginLeft: '0.25rem',
                      }}
                      aria-label={`Delete ${label.name} label`}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.opacity = '0.7';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.opacity = '1';
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
        title="Create New Label"
        isOpen={isCreateDialogOpen}
        onClose={handleCancelCreate}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateLabel}
            isLoading={isCreating}
            isDisabled={!newLabel.name || !String(newLabel.name).trim()}
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
            label="Name"
            isRequired
            fieldId="label-name"
            helperTextInvalid={createError && !newLabel.name ? createError : ''}
            validated={createError && !newLabel.name ? 'error' : 'default'}
          >
            <TextInput
              id="label-name"
              value={newLabel.name || ''}
              onChange={(value) => {
                const stringValue =
                  typeof value === 'string'
                    ? value
                    : value?.target?.value || '';
                setNewLabel((prev) => ({ ...prev, name: stringValue }));
                setCreateError(null);
              }}
              placeholder="Enter label name"
              isRequired
            />
          </FormGroup>
          <FormGroup label="Color" fieldId="label-color">
            <TextInput
              id="label-color"
              value={newLabel.color || ''}
              onChange={(value) => {
                const stringValue =
                  typeof value === 'string'
                    ? value
                    : value?.target?.value || '';
                setNewLabel((prev) => ({ ...prev, color: stringValue }));
              }}
              placeholder="Enter hex color (e.g., ffffff)"
            />
          </FormGroup>
          <FormGroup label="Description" fieldId="label-description">
            <TextArea
              id="label-description"
              value={newLabel.description || ''}
              onChange={(value) => {
                const stringValue =
                  typeof value === 'string'
                    ? value
                    : value?.target?.value || '';
                setNewLabel((prev) => ({ ...prev, description: stringValue }));
              }}
              placeholder="Enter label description (optional)"
              rows={3}
            />
          </FormGroup>
          {createError && newLabel.name && String(newLabel.name).trim() && (
            <Alert variant="danger" title="Error creating label" isInline>
              {createError}
            </Alert>
          )}
        </Form>
      </Modal>
    </>
  );
};

export default ManageLabels;
