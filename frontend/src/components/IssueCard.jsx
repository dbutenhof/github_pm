// ai-generated: Cursor
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
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
import {
  CodeBranchIcon,
  CaretDownIcon,
  CaretRightIcon,
} from '@patternfly/react-icons';
import { getDaysSince, formatDate } from '../utils/dateUtils';
import {
  fetchComments,
  fetchLabels,
  addLabel,
  removeLabel,
  createLabel,
  setIssueMilestone,
  removeIssueMilestone,
  fetchIssueReactions,
  fetchAssignees,
  setIssueAssignees,
  removeIssueAssignees,
} from '../services/api';
import CommentCard from './CommentCard';
import Reactions from './Reactions';
import UserAvatar from './UserAvatar';
import labelsCache, { clearLabelsCache } from '../utils/labelsCache';
import milestonesCache from '../utils/milestonesCache';
import assigneesCache from '../utils/assigneesCache';

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

const IssueCard = ({ issue, onMilestoneChange, onIssueUpdate }) => {
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
  const [reactions, setReactions] = useState([]);
  const [reactionsLoading, setReactionsLoading] = useState(false);
  const [reactionsError, setReactionsError] = useState(null);
  const [availableAssignees, setAvailableAssignees] = useState([]);
  const [isAssigneesMenuOpen, setIsAssigneesMenuOpen] = useState(false);
  const [assigneesLoading, setAssigneesLoading] = useState(false);
  const [assigneesError, setAssigneesError] = useState(null);
  const [currentAssignees, setCurrentAssignees] = useState(
    issue.assignees || []
  );
  const [pendingAssignees, setPendingAssignees] = useState([]); // Temporary selection while dropdown is open
  const assigneesMenuRef = useRef(null);
  const assigneesToggleRef = useRef(null);

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

  // Sync currentAssignees with issue.assignees when issue changes
  useEffect(() => {
    setCurrentAssignees(Array.isArray(issue.assignees) ? issue.assignees : []);
  }, [issue.assignees]);

  // Fetch reactions if total_count > 0
  useEffect(() => {
    // Reset reactions when issue changes
    if (issue.number) {
      setReactions([]);
      setReactionsError(null);
    }
  }, [issue.number]);

  useEffect(() => {
    if (
      issue.reactions?.total_count > 0 &&
      reactions.length === 0 &&
      !reactionsLoading
    ) {
      setReactionsLoading(true);
      setReactionsError(null);
      fetchIssueReactions(issue.number)
        .then((data) => {
          setReactions(data);
          setReactionsLoading(false);
        })
        .catch((err) => {
          setReactionsError(err.message);
          setReactionsLoading(false);
        });
    }
  }, [
    issue.reactions?.total_count,
    issue.number,
    reactions.length,
    reactionsLoading,
  ]);

  // Preload assignees when component mounts (shared cache) - non-blocking
  useEffect(() => {
    // If assignees are already cached, use them
    if (assigneesCache.data.length > 0) {
      setAvailableAssignees(assigneesCache.data);
      setAssigneesLoading(false);
      setAssigneesError(assigneesCache.error);
      return;
    }

    // If assignees are currently being fetched, subscribe to the existing promise
    if (assigneesCache.promise) {
      setAssigneesLoading(true);
      assigneesCache.promise
        .then(() => {
          setAvailableAssignees(assigneesCache.data);
          setAssigneesLoading(false);
          setAssigneesError(assigneesCache.error);
        })
        .catch(() => {
          setAssigneesLoading(false);
          setAssigneesError(assigneesCache.error);
        });
      return;
    }

    // Start fetching assignees asynchronously (non-blocking)
    if (!assigneesCache.loading) {
      assigneesCache.loading = true;
      assigneesCache.error = null;

      assigneesCache.promise = fetchAssignees()
        .then((data) => {
          assigneesCache.data = data;
          assigneesCache.loading = false;
          assigneesCache.error = null;
          assigneesCache.promise = null;
          setAvailableAssignees(data);
          setAssigneesLoading(false);
          setAssigneesError(null);
        })
        .catch((err) => {
          assigneesCache.loading = false;
          assigneesCache.error = err.message;
          assigneesCache.promise = null;
          setAssigneesLoading(false);
          setAssigneesError(err.message);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run once on mount

  // Update loading state when menu opens if assignees are still loading
  useEffect(() => {
    if (isAssigneesMenuOpen) {
      // If assignees are already cached, use them immediately
      if (assigneesCache.data.length > 0) {
        setAvailableAssignees(assigneesCache.data);
        setAssigneesLoading(false);
        setAssigneesError(assigneesCache.error);
        return;
      }

      // If assignees are still loading, show loading state and wait for promise
      if (assigneesCache.loading && assigneesCache.promise) {
        setAssigneesLoading(true);
        setAssigneesError(null);
        assigneesCache.promise
          .then(() => {
            setAvailableAssignees(assigneesCache.data);
            setAssigneesLoading(false);
            setAssigneesError(assigneesCache.error);
          })
          .catch(() => {
            setAssigneesLoading(false);
            setAssigneesError(assigneesCache.error);
          });
      } else if (!assigneesCache.loading && assigneesCache.data.length === 0) {
        // Assignees haven't been fetched yet, start fetching now
        setAssigneesLoading(true);
        assigneesCache.loading = true;
        assigneesCache.error = null;

        assigneesCache.promise = fetchAssignees()
          .then((data) => {
            assigneesCache.data = data;
            assigneesCache.loading = false;
            assigneesCache.error = null;
            assigneesCache.promise = null;
            setAvailableAssignees(data);
            setAssigneesLoading(false);
            setAssigneesError(null);
          })
          .catch((err) => {
            assigneesCache.loading = false;
            assigneesCache.error = err.message;
            assigneesCache.promise = null;
            setAssigneesLoading(false);
            setAssigneesError(err.message);
          });
      }
    }
  }, [isAssigneesMenuOpen]);

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

  // Define handleApplyAssignees before the useEffect that uses it
  const handleApplyAssignees = useCallback(async () => {
    try {
      setAssigneesError(null);
      const currentLogins = currentAssignees.map((a) => a.login);
      const pendingLogins = pendingAssignees.map((a) => a.login);

      // Check if there are any changes
      const currentSet = new Set(currentLogins);
      const pendingSet = new Set(pendingLogins);
      const hasChanges =
        currentLogins.length !== pendingLogins.length ||
        currentLogins.some((login) => !pendingSet.has(login)) ||
        pendingLogins.some((login) => !currentSet.has(login));

      if (!hasChanges) {
        // No changes, just close the dropdown
        setIsAssigneesMenuOpen(false);
        return;
      }

      // Determine which assignees were removed and which were added
      const removedLogins = currentLogins.filter(
        (login) => !pendingSet.has(login)
      );
      const addedLogins = pendingLogins.filter(
        (login) => !currentSet.has(login)
      );

      let updatedIssue;
      if (pendingLogins.length === 0) {
        // All assignees removed - use DELETE with all current assignees
        if (currentLogins.length > 0) {
          updatedIssue = await removeIssueAssignees(
            issue.number,
            currentLogins
          );
          setCurrentAssignees(updatedIssue.assignees || []);
          if (onIssueUpdate) {
            onIssueUpdate(updatedIssue);
          }
        }
      } else if (removedLogins.length > 0 && addedLogins.length === 0) {
        // Only removals, no additions - use DELETE with removed assignees
        updatedIssue = await removeIssueAssignees(issue.number, removedLogins);
        setCurrentAssignees(updatedIssue.assignees || []);
        if (onIssueUpdate) {
          onIssueUpdate(updatedIssue);
        }
      } else {
        // Additions or mixed changes - use POST to replace entire list
        updatedIssue = await setIssueAssignees(issue.number, pendingLogins);
        setCurrentAssignees(updatedIssue.assignees || []);
        if (onIssueUpdate) {
          onIssueUpdate(updatedIssue);
        }
      }
      setIsAssigneesMenuOpen(false);
    } catch (err) {
      console.error('Failed to update assignees:', err);
      setAssigneesError(err.message);
      // On error, reset pending to current
      setPendingAssignees([...currentAssignees]);
    }
  }, [currentAssignees, pendingAssignees, issue.number, onIssueUpdate]);

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
      if (
        isAssigneesMenuOpen &&
        assigneesToggleRef.current &&
        !assigneesToggleRef.current.contains(event.target) &&
        assigneesMenuRef.current &&
        !assigneesMenuRef.current.contains(event.target)
      ) {
        // Clicking outside - apply changes before closing
        handleApplyAssignees();
      }
    };

    if (isLabelMenuOpen || isMilestoneMenuOpen || isAssigneesMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [
    isLabelMenuOpen,
    isMilestoneMenuOpen,
    isAssigneesMenuOpen,
    handleApplyAssignees,
  ]);

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
    const fromMilestoneNumber =
      currentMilestone?.number ?? issue.milestone?.number ?? null;
    try {
      if (milestoneNumber === null) {
        // Remove milestone
        if (currentMilestone) {
          await removeIssueMilestone(issue.number, currentMilestone.number);
          setCurrentMilestone(null);
          if (onMilestoneChange) {
            onMilestoneChange({
              fromMilestoneNumber,
              toMilestoneNumber: null,
            });
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
          onMilestoneChange({
            fromMilestoneNumber,
            toMilestoneNumber: milestoneNumber,
          });
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

  const isAssigneeSelected = (assigneeLogin) => {
    // Use pendingAssignees if dropdown is open, otherwise use currentAssignees
    const assigneesToCheck = isAssigneesMenuOpen
      ? pendingAssignees
      : currentAssignees;
    if (!assigneesToCheck || !Array.isArray(assigneesToCheck)) {
      return false;
    }
    return assigneesToCheck.some(
      (assignee) => assignee && assignee.login === assigneeLogin
    );
  };

  // Initialize pending assignees when dropdown opens
  useEffect(() => {
    if (isAssigneesMenuOpen) {
      setPendingAssignees([...(currentAssignees || [])]);
      setAssigneesError(null);
    }
  }, [isAssigneesMenuOpen, currentAssignees]);

  const handleToggleAssignee = (assigneeLogin, isChecked) => {
    // Only update pending selection, don't make API calls yet
    setPendingAssignees((prev) => {
      const prevArray = Array.isArray(prev) ? prev : [];
      if (isChecked) {
        // Add assignee to pending selection
        const assigneeToAdd = availableAssignees.find(
          (a) => a && a.login === assigneeLogin
        );
        if (
          assigneeToAdd &&
          !prevArray.some((a) => a && a.login === assigneeLogin)
        ) {
          return [...prevArray, assigneeToAdd];
        }
        return prevArray;
      } else {
        // Remove assignee from pending selection
        return prevArray.filter((a) => a && a.login !== assigneeLogin);
      }
    });
  };

  const getCommentsToggleText = () => {
    return isCommentsExpanded
      ? `Hide Comments (${issue.comments})`
      : `Show Comments (${issue.comments})`;
  };

  // Column 4: PR icon, "closed by #<pr>", or blank
  const renderPrColumn = () => {
    if (issue.pull_request) {
      return (
        <Tooltip content="Pull Request">
          <CodeBranchIcon
            style={{
              color: '#0066cc',
              verticalAlign: 'middle',
              userSelect: 'none',
            }}
          />
        </Tooltip>
      );
    }
    if (issue.closed_by && issue.closed_by.length > 0) {
      return (
        <span style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
          closed by{' '}
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
        </span>
      );
    }
    return null;
  };

  const cellStyle = {
    padding: '0.5rem',
    verticalAlign: 'top',
    borderBottom: '1px solid #d2d2d2',
  };

  return (
    <>
      <tr>
        {/* Column 1: Expansion icon */}
        <td style={{ ...cellStyle, width: '2rem' }}>
          {issue.body_html ? (
            <Button
              variant="plain"
              onClick={() => setIsDescriptionExpanded(!isDescriptionExpanded)}
              style={{ padding: '0.125rem' }}
              aria-expanded={isDescriptionExpanded}
              aria-label={
                isDescriptionExpanded ? 'Hide description' : 'Show description'
              }
            >
              {isDescriptionExpanded ? (
                <CaretDownIcon style={{ fontSize: '1rem' }} />
              ) : (
                <CaretRightIcon style={{ fontSize: '1rem' }} />
              )}
            </Button>
          ) : null}
        </td>

        {/* Column 2: Issue number link */}
        <td style={cellStyle}>
          <a
            href={issue.html_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              textDecoration: 'none',
              color: '#0066cc',
              fontWeight: '500',
              whiteSpace: 'nowrap',
            }}
          >
            #{issue.number}
          </a>
        </td>

        {/* Column 3: Owner avatar, creation date, assigned chiclet stacked */}
        <td style={cellStyle}>
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: '0.5rem',
              flexWrap: 'wrap',
            }}
          >
            {issue.user ? (
              issue.user.html_url ? (
                <a
                  href={issue.user.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    color: '#0066cc',
                  }}
                >
                  <UserAvatar user={issue.user} size={28} />
                  <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
                    {issue.user.login || 'Unknown'}
                  </span>
                </a>
              ) : (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <UserAvatar user={issue.user} size={28} />
                  <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
                    {issue.user.login || 'Unknown'}
                  </span>
                </span>
              )
            ) : (
              <span style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
                Unknown
              </span>
            )}
            <div
              ref={assigneesToggleRef}
              style={{
                position: 'relative',
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              <Button
                variant={currentAssignees.length > 0 ? 'primary' : 'secondary'}
                onClick={() => {
                  if (isAssigneesMenuOpen) {
                    // Closing dropdown - apply changes
                    handleApplyAssignees();
                  } else {
                    // Opening dropdown - initialize pending selection
                    setIsAssigneesMenuOpen(true);
                  }
                }}
                style={{
                  padding: '0.125rem 0.5rem',
                  fontSize: '0.75rem',
                  minWidth: 'auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                {currentAssignees.length > 0 ? (
                  <>
                    {currentAssignees.map((a) => (
                      <UserAvatar key={a.login} user={a} size={18} />
                    ))}
                    <span>
                      Assigned to{' '}
                      {currentAssignees.map((a) => a.login).join(', ')}
                    </span>
                  </>
                ) : (
                  'Unassigned'
                )}
              </Button>
              {isAssigneesMenuOpen && (
                <div
                  ref={assigneesMenuRef}
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: '0',
                    marginTop: '0.25rem',
                    backgroundColor: '#fff',
                    border: '1px solid #d2d2d2',
                    borderRadius: '0.25rem',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                    zIndex: 1000,
                    minWidth: '200px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    cursor: assigneesLoading ? 'wait' : 'default',
                  }}
                >
                  <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    {assigneesLoading && (
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
                          Loading assignees...
                        </div>
                      </div>
                    )}
                    {assigneesError && (
                      <div style={{ padding: '0.5rem' }}>
                        <Alert
                          variant="danger"
                          title="Error loading assignees"
                          isInline
                        >
                          {assigneesError}
                        </Alert>
                      </div>
                    )}
                    {!assigneesLoading &&
                      !assigneesError &&
                      availableAssignees.map((assignee) => {
                        const isSelected = isAssigneeSelected(assignee.login);
                        return (
                          <div
                            key={assignee.id || assignee.login}
                            style={{
                              padding: '0.5rem',
                              cursor: 'pointer',
                              backgroundColor: isSelected
                                ? '#f0f0f0'
                                : 'transparent',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem',
                            }}
                            onClick={(e) => {
                              // Only toggle if clicking on the row background, not on checkbox, label, or link
                              const target = e.target;
                              const isCheckbox =
                                target.type === 'checkbox' ||
                                target.closest('input[type="checkbox"]');
                              const isLabel = target.closest('label');
                              const isLink = target.closest('a');

                              if (!isCheckbox && !isLabel && !isLink) {
                                handleToggleAssignee(
                                  assignee.login,
                                  !isSelected
                                );
                              }
                            }}
                            onMouseEnter={(e) => {
                              if (!isSelected) {
                                e.currentTarget.style.backgroundColor =
                                  '#f0f0f0';
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (!isSelected) {
                                e.currentTarget.style.backgroundColor =
                                  'transparent';
                              }
                            }}
                          >
                            <div
                              onClick={(e) => {
                                // Stop propagation for the entire checkbox area
                                e.stopPropagation();
                              }}
                            >
                              <Checkbox
                                isChecked={!!isSelected}
                                onClick={(e) => {
                                  // Stop propagation to prevent row click handler
                                  e.stopPropagation();
                                  // Handle the toggle directly - this ensures it works for both select and deselect
                                  handleToggleAssignee(
                                    assignee.login,
                                    !isSelected
                                  );
                                }}
                                label={
                                  <span
                                    style={{
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: '0.5rem',
                                    }}
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    <UserAvatar user={assignee} size={20} />
                                    <a
                                      href={assignee.html_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{
                                        textDecoration: 'none',
                                        color: '#0066cc',
                                      }}
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {assignee.login}
                                    </a>
                                  </span>
                                }
                                id={`assignee-${assignee.login}`}
                              />
                            </div>
                          </div>
                        );
                      })}
                    {!assigneesLoading &&
                      !assigneesError &&
                      availableAssignees.length === 0 && (
                        <div
                          style={{
                            padding: '0.5rem',
                            color: '#6a6e73',
                            fontStyle: 'italic',
                          }}
                        >
                          No assignees available
                        </div>
                      )}
                  </div>
                </div>
              )}
            </div>
          </div>
          <span
            style={{
              display: 'block',
              fontSize: '0.7rem',
              color: '#6a6e73',
              marginTop: '0.2rem',
            }}
          >
            {formatDate(issue.created_at)} ({daysSince} days ago)
          </span>
        </td>

        {/* Column 4: PR icon or closed by #pr or blank */}
        <td style={cellStyle}>{renderPrColumn()}</td>

        {/* Column 5: Milestone control */}
        <td style={cellStyle}>
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
        </td>

        {/* Column 6: Label chiclets - flow side-by-side when they fit */}
        <td style={cellStyle}>
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              flexWrap: 'wrap',
              gap: '0.25rem',
              alignItems: 'center',
            }}
          >
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
          </div>
        </td>

        {/* Column 7: Issue title - wraps to fit page width */}
        <td
          style={{
            ...cellStyle,
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
          }}
        >
          {issue.type && (
            <Tooltip content={issue.type.description || ''}>
              <span
                style={{
                  display: 'inline-block',
                  marginRight: '0.5rem',
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
          <span style={{ fontWeight: '500' }}>{issue.title}</span>
        </td>
      </tr>

      {/* Expanded description and comments - only shown when expanded */}
      {issue.body_html && isDescriptionExpanded && (
        <tr>
          <td
            colSpan={7}
            style={{
              padding: '0.75rem',
              borderBottom: '1px solid #d2d2d2',
              backgroundColor: '#fafafa',
            }}
          >
            <div
              style={{ paddingTop: '0.5rem' }}
              dangerouslySetInnerHTML={{ __html: issue.body_html }}
            />
            {issue.comments > 0 && (
              <div style={{ marginTop: issue.body_html ? '1rem' : '0rem' }}>
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
            {issue.reactions?.total_count > 0 && (
              <div style={{ marginTop: '0.75rem' }}>
                {reactionsLoading && (
                  <div style={{ textAlign: 'center', padding: '0.5rem' }}>
                    <Spinner size="sm" />
                  </div>
                )}
                {reactionsError && (
                  <Alert
                    variant="danger"
                    title="Error loading reactions"
                    isInline
                  >
                    {reactionsError}
                  </Alert>
                )}
                {!reactionsLoading &&
                  !reactionsError &&
                  reactions.length > 0 && <Reactions reactions={reactions} />}
              </div>
            )}
          </td>
        </tr>
      )}
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
    </>
  );
};

export default IssueCard;
