// ai-generated: Cursor
import React, { useState, useEffect, useRef } from 'react';
import { Modal, Button, Tooltip, Spinner, Alert } from '@patternfly/react-core';
import { fetchLabels } from '../services/api';
import labelsCache from '../utils/labelsCache';

const ManageSort = ({ isOpen, onClose, sortOrder, onSortChange }) => {
  const [allLabels, setAllLabels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [dragOverIndex, setDragOverIndex] = useState(null);
  const dragItemRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      loadLabels();
    }
  }, [isOpen]);

  const loadLabels = () => {
    // Use cached data if available
    if (labelsCache.data.length > 0) {
      setAllLabels(labelsCache.data);
      setLoading(false);
      setError(labelsCache.error);
      return;
    }

    // If data is being loaded, wait for it
    if (labelsCache.promise) {
      setLoading(true);
      labelsCache.promise
        .then(() => {
          setAllLabels(labelsCache.data);
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
        setAllLabels(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  // Get current sort order labels (in order) and available labels (not in sort order)
  const getCurrentSortLabels = () => {
    return sortOrder
      .map((labelName) => allLabels.find((l) => l.name === labelName))
      .filter((label) => label !== undefined);
  };

  const getAvailableLabels = () => {
    const currentLabelNames = new Set(sortOrder);
    return allLabels.filter((label) => !currentLabelNames.has(label.name));
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    dragItemRef.current = index;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target);
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  const handleDrop = (e, dropIndex) => {
    e.preventDefault();
    setDragOverIndex(null);

    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null);
      return;
    }

    const currentSortLabels = getCurrentSortLabels();
    const newSortLabels = [...currentSortLabels];
    const draggedItem = newSortLabels[draggedIndex];
    newSortLabels.splice(draggedIndex, 1);
    newSortLabels.splice(dropIndex, 0, draggedItem);

    const newSortOrder = newSortLabels.map((label) => label.name);
    onSortChange(newSortOrder);
    setDraggedIndex(null);
  };

  const handleRemoveLabel = (labelName) => {
    const newSortOrder = sortOrder.filter((name) => name !== labelName);
    onSortChange(newSortOrder);
  };

  const handleAddLabel = (labelName) => {
    const newSortOrder = [...sortOrder, labelName];
    onSortChange(newSortOrder);
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

  const currentSortLabels = getCurrentSortLabels();
  const availableLabels = getAvailableLabels();

  return (
    <Modal
      title="Sort Issues by Labels"
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
        <p style={{ marginBottom: '0.5rem', color: '#6a6e73' }}>
          Drag labels to reorder. Issues will be sorted by labels in the order
          shown below. Click on labels in the "Available Labels" section to add
          them.
        </p>
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
        <div>
          {currentSortLabels.length === 0 ? (
            <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
              No labels in sort order. Click "+ Add Label" to add labels.
            </p>
          ) : (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              {currentSortLabels.map((label, index) => (
                <div
                  key={label.name}
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, index)}
                  onDragEnd={() => {
                    setDraggedIndex(null);
                    setDragOverIndex(null);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem',
                    backgroundColor:
                      dragOverIndex === index
                        ? '#f0f0f0'
                        : draggedIndex === index
                          ? '#e0e0e0'
                          : '#fff',
                    border: '1px solid #d2d2d2',
                    borderRadius: '0.25rem',
                    cursor: 'move',
                    opacity: draggedIndex === index ? 0.5 : 1,
                    transition: 'background-color 0.2s',
                  }}
                >
                  <span
                    style={{
                      fontSize: '1rem',
                      color: '#6a6e73',
                      userSelect: 'none',
                    }}
                  >
                    ⋮⋮
                  </span>
                  <Tooltip content={label.description || 'No description'}>
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
                        flex: 1,
                      }}
                    >
                      {label.name}
                    </span>
                  </Tooltip>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveLabel(label.name);
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
                      width: '24px',
                      height: '24px',
                    }}
                    aria-label={`Remove ${label.name} from sort order`}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = '#c9190b';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = '#6a6e73';
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {availableLabels.length > 0 && (
            <div style={{ marginTop: '2rem' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>
                Available Labels
              </h3>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                {availableLabels.map((label) => (
                  <Tooltip
                    key={label.name}
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
                        cursor: 'pointer',
                      }}
                      onClick={() => handleAddLabel(label.name)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.opacity = '0.8';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.opacity = '1';
                      }}
                    >
                      + {label.name}
                    </span>
                  </Tooltip>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

export default ManageSort;
