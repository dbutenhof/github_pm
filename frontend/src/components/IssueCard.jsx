// ai-generated: Cursor
import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  ExpandableSection,
  Spinner,
  Alert,
  Tooltip,
  Button,
  Checkbox,
  Modal,
  TextInput,
  TextArea,
  Form,
  FormGroup,
} from '@patternfly/react-core';
import { CodeBranchIcon } from '@patternfly/react-icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getDaysSince, formatDate } from '../utils/dateUtils';
import {
  fetchComments,
  fetchLabels,
  addLabel,
  removeLabel,
  createLabel,
  setIssueMilestone,
  removeIssueMilestone,
} from '../services/api';
import CommentCard from './CommentCard';
import labelsCache, { clearLabelsCache } from '../utils/labelsCache';
import milestonesCache from '../utils/milestonesCache';

const getContrastColor = (hexColor) => {
  // Convert hex to RGB
  const r = parseInt(hexColor.substring(0, 2), 16);
  const g = parseInt(hexColor.substring(2, 4), 16);
  const b = parseInt(hexColor.substring(4, 6), 16);
  // Calculate luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  // Return black for light colors, white for dark colors
  return luminance > 0.5 ? '#000000' : '#ffffff';
};

const getTypeContrastColor = (colorName) => {
  // Common dark HTML color names that need white text
  const darkColors = [
    'blue',
    'red',
    'green',
    'purple',
    'navy',
    'maroon',
    'olive',
    'teal',
    'black',
    'darkblue',
    'darkgreen',
    'darkred',
    'darkviolet',
    'indigo',
  ];
  // Check if it's a hex color (starts with # or is 6 hex digits)
  if (colorName.startsWith('#') || /^[0-9A-Fa-f]{6}$/.test(colorName)) {
    const hex = colorName.startsWith('#') ? colorName.substring(1) : colorName;
    return getContrastColor(hex);
  }
  // For named colors, use white for dark colors, black for light colors
  return darkColors.includes(colorName.toLowerCase()) ? '#ffffff' : '#000000';
};

const IssueCard = ({ issue, onMilestoneChange }) => {
  const daysSince = getDaysSince(issue.created_at);
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [isCommentsExpanded, setIsCommentsExpanded] = useState(false);
  const [comments, setComments] = useState([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentsError, setCommentsError] = useState(null);
  const [currentLabels, setCurrentLabels] = useState(issue.labels || []);
  const [availableLabels, setAvailableLabels] = useState([]);
  const [isLabelMenuOpen, setIsLabelMenuOpen] = useState(false);
  const [labelsLoading, setLabelsLoading] = useState(false);
  const [labelsError, setLabelsError] = useState(null);
  const [labelSearchFilter, setLabelSearchFilter] = useState('');
  const [isCreateLabelDialogOpen, setIsCreateLabelDialogOpen] = useState(false);
  const [newLabel, setNewLabel] = useState({
    name: '',
    color: '',
    description: '',
  });
  const [createLabelError, setCreateLabelError] = useState(null);
  const [isCreatingLabel, setIsCreatingLabel] = useState(false);
  const [currentMilestone, setCurrentMilestone] = useState(issue.milestone);
  const [isMilestoneMenuOpen, setIsMilestoneMenuOpen] = useState(false);
  const milestoneMenuRef = useRef(null);
  const milestoneToggleRef = useRef(null);
  const menuRef = useRef(null);
  const toggleRef = useRef(null);

  useEffect(() => {
    if (
      isCommentsExpanded &&
      comments.length === 0 &&
      !commentsLoading &&
      issue.comments > 0
    ) {
      setCommentsLoading(true);
      setCommentsError(null);
      fetchComments(issue.number)
        .then((data) => {
          setComments(data);
          setCommentsLoading(false);
        })
        .catch((err) => {
          setCommentsError(err.message);
          setCommentsLoading(false);
        });
    }
  }, [
    isCommentsExpanded,
    issue.number,
    issue.comments,
    comments.length,
    commentsLoading,
  ]);

  // Collapse comments when description is collapsed
  useEffect(() => {
    if (!isDescriptionExpanded) {
      setIsCommentsExpanded(false);
    }
  }, [isDescriptionExpanded]);

  // Sync currentLabels with issue.labels when issue changes
  useEffect(() => {
    setCurrentLabels(issue.labels || []);
  }, [issue.labels]);

  // Sync currentMilestone with issue.milestone when issue changes
  useEffect(() => {
    setCurrentMilestone(issue.milestone);
  }, [issue.milestone]);

  // Preload labels when component mounts (shared cache) - non-blocking
  // useEffect runs after render, so this won't block the initial render
  useEffect(() => {
    // If labels are already cached, use them
    if (labelsCache.data.length > 0) {
      setAvailableLabels(labelsCache.data);
      setLabelsLoading(false);
      setLabelsError(labelsCache.error);
      return;
    }

    // If labels are currently being fetched, subscribe to the existing promise
    if (labelsCache.promise) {
      setLabelsLoading(true);
      labelsCache.promise
        .then(() => {
          setAvailableLabels(labelsCache.data);
          setLabelsLoading(false);
          setLabelsError(labelsCache.error);
        })
        .catch(() => {
          setLabelsLoading(false);
          setLabelsError(labelsCache.error);
        });
      return;
    }

    // Start fetching labels asynchronously (non-blocking - fetchLabels is async)
    if (!labelsCache.loading) {
      labelsCache.loading = true;
      labelsCache.error = null;

      labelsCache.promise = fetchLabels()
        .then((data) => {
          labelsCache.data = data;
          labelsCache.loading = false;
          labelsCache.error = null;
          labelsCache.promise = null;
          // Update all components that might be listening
          setAvailableLabels(data);
          setLabelsLoading(false);
          setLabelsError(null);
        })
        .catch((err) => {
          labelsCache.loading = false;
          labelsCache.error = err.message;
          labelsCache.promise = null;
          setLabelsLoading(false);
          setLabelsError(err.message);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run once on mount

  // Update loading state when menu opens if labels are still loading
  useEffect(() => {
    if (isLabelMenuOpen) {
      // If labels are already cached, use them immediately
      if (labelsCache.data.length > 0) {
        setAvailableLabels(labelsCache.data);
        setLabelsLoading(false);
        setLabelsError(labelsCache.error);
        return;
      }

      // If labels are still loading, show loading state and wait for promise
      if (labelsCache.loading && labelsCache.promise) {
        setLabelsLoading(true);
        setLabelsError(null);
        // Subscribe to the existing promise
        labelsCache.promise
          .then(() => {
            setAvailableLabels(labelsCache.data);
            setLabelsLoading(false);
            setLabelsError(labelsCache.error);
          })
          .catch(() => {
            setLabelsLoading(false);
            setLabelsError(labelsCache.error);
          });
      } else if (!labelsCache.loading && labelsCache.data.length === 0) {
        // Labels haven't been fetched yet, start fetching now
        setLabelsLoading(true);
        labelsCache.loading = true;
        labelsCache.error = null;

        labelsCache.promise = fetchLabels()
          .then((data) => {
            labelsCache.data = data;
            labelsCache.loading = false;
            labelsCache.error = null;
            labelsCache.promise = null;
            setAvailableLabels(data);
            setLabelsLoading(false);
            setLabelsError(null);
          })
          .catch((err) => {
            labelsCache.loading = false;
            labelsCache.error = err.message;
            labelsCache.promise = null;
            setLabelsLoading(false);
            setLabelsError(err.message);
          });
      }
    }
  }, [isLabelMenuOpen]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        isLabelMenuOpen &&
        toggleRef.current &&
        !toggleRef.current.contains(event.target) &&
        menuRef.current &&
        !menuRef.current.contains(event.target)
      ) {
        setIsLabelMenuOpen(false);
        setLabelSearchFilter('');
      }
      if (
        isMilestoneMenuOpen &&
        milestoneToggleRef.current &&
        !milestoneToggleRef.current.contains(event.target) &&
        milestoneMenuRef.current &&
        !milestoneMenuRef.current.contains(event.target)
      ) {
        setIsMilestoneMenuOpen(false);
      }
    };

    if (isLabelMenuOpen || isMilestoneMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isLabelMenuOpen, isMilestoneMenuOpen]);

  const handleRemoveLabel = async (labelName) => {
    try {
      await removeLabel(issue.number, labelName);
      setCurrentLabels(
        currentLabels.filter((label) => label.name !== labelName)
      );
    } catch (err) {
      console.error('Failed to remove label:', err);
      setLabelsError(err.message);
    }
  };

  const handleToggleLabel = async (labelName, isChecked) => {
    try {
      if (isChecked) {
        await addLabel(issue.number, labelName);
        const labelToAdd = availableLabels.find((l) => l.name === labelName);
        if (labelToAdd) {
          setCurrentLabels([...currentLabels, labelToAdd]);
        }
      } else {
        await removeLabel(issue.number, labelName);
        setCurrentLabels(
          currentLabels.filter((label) => label.name !== labelName)
        );
      }
    } catch (err) {
      console.error('Failed to toggle label:', err);
      setLabelsError(err.message);
    }
  };

  const refreshLabels = async () => {
    // Clear cache and reload labels
    clearLabelsCache();

    setLabelsLoading(true);
    setLabelsError(null);
    try {
      const data = await fetchLabels();
      labelsCache.data = data;
      labelsCache.loading = false;
      labelsCache.error = null;
      labelsCache.promise = null;
      setAvailableLabels(data);
      setLabelsLoading(false);
      setLabelsError(null);
    } catch (err) {
      labelsCache.loading = false;
      labelsCache.error = err.message;
      labelsCache.promise = null;
      setLabelsLoading(false);
      setLabelsError(err.message);
    }
  };

  const handleCreateLabel = async () => {
    const name = String(newLabel.name || '').trim();
    if (!name) {
      setCreateLabelError('Name is required');
      return;
    }

    setIsCreatingLabel(true);
    setCreateLabelError(null);

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

      await createLabel(labelData);
      setIsCreateLabelDialogOpen(false);
      setNewLabel({ name: '', color: '', description: '' });
      setCreateLabelError(null);
      // Refresh labels list
      await refreshLabels();
    } catch (err) {
      setCreateLabelError(err.message);
    } finally {
      setIsCreatingLabel(false);
    }
  };

  const handleCancelCreateLabel = () => {
    setIsCreateLabelDialogOpen(false);
    setNewLabel({ name: '', color: '', description: '' });
    setCreateLabelError(null);
  };

  const handleMilestoneChange = async (milestoneNumber) => {
    try {
      if (milestoneNumber === null) {
        // Remove milestone
        if (currentMilestone) {
          await removeIssueMilestone(issue.number, currentMilestone.number);
          setCurrentMilestone(null);
          if (onMilestoneChange) {
            onMilestoneChange();
          }
        }
      } else {
        // Set milestone
        await setIssueMilestone(issue.number, milestoneNumber);
        const newMilestone = milestonesCache.data.find(
          (m) => m.number === milestoneNumber
        );
        if (newMilestone) {
          setCurrentMilestone(newMilestone);
        }
        if (onMilestoneChange) {
          onMilestoneChange();
        }
      }
    } catch (err) {
      console.error('Failed to change milestone:', err);
      // Restore previous milestone on error
      setCurrentMilestone(issue.milestone);
    }
  };

  const isLabelSelected = (labelName) => {
    return currentLabels.some((label) => label.name === labelName);
  };

  const getToggleText = () => {
    const baseText = isDescriptionExpanded
      ? 'Hide Description'
      : 'Show Description';
    if (issue.comments > 0) {
      return `${baseText} (${issue.comments} ${issue.comments === 1 ? 'comment' : 'comments'})`;
    }
    return baseText;
  };

  const getCommentsToggleText = () => {
    return isCommentsExpanded
      ? `Hide Comments (${issue.comments})`
      : `Show Comments (${issue.comments})`;
  };

  return (
    <Card
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <CardHeader>
        <CardTitle>
          <a
            href={issue.html_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: 'none', color: '#0066cc' }}
          >
            #{issue.number}
          </a>
          {issue.pull_request && (
            <Tooltip content="Pull Request">
              <CodeBranchIcon
                style={{
                  marginLeft: '0.5rem',
                  color: '#0066cc',
                  verticalAlign: 'middle',
                  userSelect: 'none',
                }}
              />
            </Tooltip>
          )}
          {issue.closed_by && issue.closed_by.length > 0 && (
            <span style={{ marginLeft: '0.5rem', color: '#6a6e73' }}>
              (closed by{' '}
              {issue.closed_by.map((pr, index) => (
                <React.Fragment key={pr.number}>
                  {index > 0 && ', '}
                  <Tooltip content={pr.title || ''}>
                    <a
                      href={pr.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        textDecoration: 'none',
                        color: '#0066cc',
                      }}
                    >
                      #{pr.number}
                    </a>
                  </Tooltip>
                </React.Fragment>
              ))}
              )
            </span>
          )}
          {' - '}
          {issue.title}
          {issue.type && (
            <Tooltip content={issue.type.description || ''}>
              <span
                style={{
                  display: 'inline-block',
                  marginLeft: '0.5rem',
                  padding: '0.125rem 0.5rem',
                  fontSize: '0.75rem',
                  fontWeight: '500',
                  borderRadius: '0.25rem',
                  backgroundColor: issue.type.color,
                  color: getTypeContrastColor(issue.type.color),
                  whiteSpace: 'nowrap',
                  cursor: issue.type.description ? 'help' : 'default',
                }}
              >
                {issue.type.name}
              </span>
            </Tooltip>
          )}
        </CardTitle>
      </CardHeader>
      <CardBody
        style={{
          flex: '1',
          overflow: 'auto',
          padding: '0rem',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            marginBottom: '0rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem',
            padding: '0.75rem',
          }}
        >
          {issue.user?.avatar_url && (
            <img
              src={issue.user.avatar_url}
              alt={issue.user.login}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                flexShrink: 0,
              }}
            />
          )}
          <div style={{ flex: '1', minWidth: 0 }}>
            <div style={{ fontWeight: '500' }}>
              {issue.user?.login || 'Unknown'}
            </div>
            <div style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
              {formatDate(issue.created_at)} ({daysSince} days ago)
            </div>
          </div>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
              gap: '0.5rem',
              maxWidth: '50%',
            }}
          >
            {/* Milestone control */}
            <div
              ref={milestoneToggleRef}
              style={{ position: 'relative', display: 'inline-block' }}
            >
              <Button
                variant={currentMilestone ? 'primary' : 'secondary'}
                onClick={() => setIsMilestoneMenuOpen(!isMilestoneMenuOpen)}
                style={{
                  padding: '0.25rem 0.75rem',
                  fontSize: '0.75rem',
                  minWidth: 'auto',
                }}
              >
                {currentMilestone ? currentMilestone.title : 'No Milestone'}
              </Button>
              {isMilestoneMenuOpen && (
                <div
                  ref={milestoneMenuRef}
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: '0',
                    marginTop: '0.25rem',
                    backgroundColor: '#fff',
                    border: '1px solid #d2d2d2',
                    borderRadius: '0.25rem',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                    zIndex: 1000,
                    minWidth: '200px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                  }}
                >
                  <div
                    style={{
                      padding: '0.5rem',
                      cursor: 'pointer',
                      borderBottom: '1px solid #d2d2d2',
                      backgroundColor:
                        currentMilestone === null ? '#f0f0f0' : 'transparent',
                    }}
                    onClick={() => {
                      handleMilestoneChange(null);
                      setIsMilestoneMenuOpen(false);
                    }}
                    onMouseEnter={(e) => {
                      if (currentMilestone !== null) {
                        e.currentTarget.style.backgroundColor = '#f0f0f0';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (currentMilestone !== null) {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <span style={{ fontSize: '0.875rem', fontStyle: 'italic' }}>
                      No Milestone
                    </span>
                  </div>
                  {milestonesCache.data.map((milestone) => (
                    <div
                      key={milestone.number}
                      style={{
                        padding: '0.5rem',
                        cursor: 'pointer',
                        backgroundColor:
                          currentMilestone?.number === milestone.number
                            ? '#f0f0f0'
                            : 'transparent',
                      }}
                      onClick={() => {
                        handleMilestoneChange(milestone.number);
                        setIsMilestoneMenuOpen(false);
                      }}
                      onMouseEnter={(e) => {
                        if (currentMilestone?.number !== milestone.number) {
                          e.currentTarget.style.backgroundColor = '#f0f0f0';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (currentMilestone?.number !== milestone.number) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }
                      }}
                    >
                      <span style={{ fontSize: '0.875rem' }}>
                        {milestone.title}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {/* Labels */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '0.25rem',
                justifyContent: 'flex-end',
                alignItems: 'flex-start',
              }}
            >
              {currentLabels.map((label) => (
                <Tooltip
                  key={label.id || label.name}
                  content={label.description || ''}
                >
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.125rem 0.25rem 0.125rem 0.5rem',
                      fontSize: '0.75rem',
                      fontWeight: '500',
                      borderRadius: '0.25rem',
                      backgroundColor: `#${label.color}`,
                      color: getContrastColor(label.color),
                      whiteSpace: 'nowrap',
                      cursor: label.description ? 'help' : 'default',
                    }}
                  >
                    {label.name}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveLabel(label.name);
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
                      }}
                      aria-label={`Remove ${label.name} label`}
                    >
                      ×
                    </button>
                  </span>
                </Tooltip>
              ))}
              <div
                ref={toggleRef}
                style={{ position: 'relative', display: 'inline-block' }}
              >
                <Button
                  variant="secondary"
                  onClick={() => {
                    setIsLabelMenuOpen(!isLabelMenuOpen);
                    if (isLabelMenuOpen) {
                      setLabelSearchFilter('');
                    }
                  }}
                  style={{
                    padding: '0.125rem 0.5rem',
                    fontSize: '0.75rem',
                    minWidth: 'auto',
                  }}
                >
                  +
                </Button>
                {isLabelMenuOpen && (
                  <div
                    ref={menuRef}
                    style={{
                      position: 'absolute',
                      top: '100%',
                      right: '0',
                      marginTop: '0.25rem',
                      backgroundColor: '#fff',
                      border: '1px solid #d2d2d2',
                      borderRadius: '0.25rem',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                      zIndex: 1000,
                      maxHeight: '300px',
                      minWidth: '250px',
                      display: 'flex',
                      flexDirection: 'column',
                      cursor: labelsLoading ? 'wait' : 'default',
                    }}
                  >
                    {/* Header with search and create button */}
                    <div
                      style={{
                        padding: '0.5rem',
                        borderBottom: '1px solid #d2d2d2',
                        display: 'flex',
                        gap: '0.5rem',
                        alignItems: 'center',
                      }}
                    >
                      <TextInput
                        value={labelSearchFilter}
                        onChange={(value) => {
                          const stringValue =
                            typeof value === 'string'
                              ? value
                              : value?.target?.value || '';
                          setLabelSearchFilter(stringValue);
                        }}
                        placeholder="Search labels..."
                        style={{ flex: 1 }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <Button
                        variant="secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          setIsCreateLabelDialogOpen(true);
                        }}
                        style={{
                          padding: '0.25rem 0.5rem',
                          fontSize: '0.75rem',
                          minWidth: 'auto',
                        }}
                      >
                        +
                      </Button>
                    </div>
                    {/* Labels list */}
                    <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
                      {labelsLoading && (
                        <div
                          style={{
                            padding: '1rem',
                            textAlign: 'center',
                            cursor: 'wait',
                          }}
                        >
                          <Spinner size="sm" />
                          <div
                            style={{
                              marginTop: '0.5rem',
                              fontSize: '0.875rem',
                              color: '#6a6e73',
                            }}
                          >
                            Loading labels...
                          </div>
                        </div>
                      )}
                      {labelsError && (
                        <div style={{ padding: '0.5rem' }}>
                          <Alert
                            variant="danger"
                            title="Error loading labels"
                            isInline
                          >
                            {labelsError}
                          </Alert>
                        </div>
                      )}
                      {!labelsLoading &&
                        !labelsError &&
                        availableLabels
                          .filter((label) => {
                            if (!labelSearchFilter) return true;
                            return label.name
                              .toLowerCase()
                              .includes(labelSearchFilter.toLowerCase());
                          })
                          .map((label) => {
                            const isSelected = isLabelSelected(label.name);
                            return (
                              <Tooltip
                                key={label.id || label.name}
                                content={label.description || ''}
                                position="right"
                              >
                                <div
                                  style={{
                                    padding: '0.5rem',
                                    cursor: isSelected
                                      ? 'not-allowed'
                                      : 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    opacity: isSelected ? 0.6 : 1,
                                  }}
                                  onMouseEnter={(e) => {
                                    if (!isSelected) {
                                      e.currentTarget.style.backgroundColor =
                                        '#f0f0f0';
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.backgroundColor =
                                      'transparent';
                                  }}
                                >
                                  <Checkbox
                                    isChecked={isSelected}
                                    onChange={(checked) => {
                                      if (!isSelected) {
                                        handleToggleLabel(label.name, checked);
                                      }
                                    }}
                                    isDisabled={isSelected}
                                    label={
                                      <span
                                        style={{
                                          display: 'inline-flex',
                                          alignItems: 'center',
                                          gap: '0.5rem',
                                        }}
                                      >
                                        <span
                                          style={{
                                            display: 'inline-block',
                                            width: '12px',
                                            height: '12px',
                                            borderRadius: '2px',
                                            backgroundColor: `#${label.color}`,
                                            flexShrink: 0,
                                          }}
                                        />
                                        {label.name}
                                      </span>
                                    }
                                    id={`label-${label.name}`}
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                </div>
                              </Tooltip>
                            );
                          })}
                      {!labelsLoading &&
                        !labelsError &&
                        availableLabels.filter((label) => {
                          if (!labelSearchFilter) return true;
                          return label.name
                            .toLowerCase()
                            .includes(labelSearchFilter.toLowerCase());
                        }).length === 0 && (
                          <div
                            style={{
                              padding: '0.5rem',
                              color: '#6a6e73',
                              fontStyle: 'italic',
                            }}
                          >
                            No labels found
                          </div>
                        )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <div
          style={{
            marginTop: 'auto',
            paddingTop: '0.5rem',
            borderTop: '1px solid #d2d2d2',
            paddingLeft: '0.75rem',
            paddingRight: '0.75rem',
            paddingBottom: '0.75rem',
          }}
        >
          {issue.body && (
            <ExpandableSection
              toggleText={getToggleText()}
              onToggle={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
              isExpanded={isDescriptionExpanded}
            >
              <div style={{ paddingTop: '0.5rem' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {issue.body}
                </ReactMarkdown>
              </div>
            </ExpandableSection>
          )}
          {issue.comments > 0 && isDescriptionExpanded && (
            <div style={{ marginTop: issue.body ? '1rem' : '0rem' }}>
              <ExpandableSection
                toggleText={getCommentsToggleText()}
                onToggle={() => setIsCommentsExpanded(!isCommentsExpanded)}
                isExpanded={isCommentsExpanded}
              >
                <div style={{ paddingTop: '0.5rem' }}>
                  {commentsLoading && (
                    <div style={{ textAlign: 'center', padding: '1rem' }}>
                      <Spinner size="md" />
                    </div>
                  )}
                  {commentsError && (
                    <Alert variant="danger" title="Error loading comments">
                      {commentsError}
                    </Alert>
                  )}
                  {!commentsLoading &&
                    !commentsError &&
                    comments.length > 0 && (
                      <div>
                        {comments.map((comment) => (
                          <CommentCard key={comment.id} comment={comment} />
                        ))}
                      </div>
                    )}
                  {!commentsLoading &&
                    !commentsError &&
                    comments.length === 0 &&
                    isCommentsExpanded && (
                      <p style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                        No comments found.
                      </p>
                    )}
                </div>
              </ExpandableSection>
            </div>
          )}
        </div>
      </CardBody>
      <Modal
        title="Create New Label"
        isOpen={isCreateLabelDialogOpen}
        onClose={handleCancelCreateLabel}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateLabel}
            isLoading={isCreatingLabel}
            isDisabled={!newLabel.name || !String(newLabel.name).trim()}
          >
            Create
          </Button>,
          <Button key="cancel" variant="link" onClick={handleCancelCreateLabel}>
            Cancel
          </Button>,
        ]}
      >
        <Form>
          <FormGroup
            label="Name"
            isRequired
            fieldId="label-name"
            helperTextInvalid={
              createLabelError && !newLabel.name ? createLabelError : ''
            }
            validated={createLabelError && !newLabel.name ? 'error' : 'default'}
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
                setCreateLabelError(null);
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
          {createLabelError &&
            newLabel.name &&
            String(newLabel.name).trim() && (
              <Alert variant="danger" title="Error creating label" isInline>
                {createLabelError}
              </Alert>
            )}
        </Form>
      </Modal>
    </Card>
  );
};

export default IssueCard;
