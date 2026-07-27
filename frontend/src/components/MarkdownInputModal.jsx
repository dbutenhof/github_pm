// Generated-by: Cursor
import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Button,
  Tabs,
  Tab,
  TabTitleText,
  TextInput,
  TextArea,
  Form,
  FormGroup,
  Checkbox,
  Spinner,
  Alert,
  Tooltip,
} from '@patternfly/react-core';
import { renderMarkdown, fetchLabels, fetchAssignees } from '../services/api';
import labelsCache from '../utils/labelsCache';
import assigneesCache from '../utils/assigneesCache';
import UserAvatar from './UserAvatar';

const ISSUE_TYPES = ['Bug', 'Feature'];

/**
 * Popup input window with Edit / Preview markdown tabs.
 *
 * Modes:
 * - comment: body only; actions Submit + optional Close with Comment + Cancel
 * - issue: title, type, labels, assignees + body; action Submit + Cancel
 *
 * Generated-by: Cursor
 * Assisted-by: Cursor
 */
const MarkdownInputModal = ({
  isOpen,
  onClose,
  mode = 'comment',
  title = 'Add Comment',
  submitLabel = 'Submit',
  onSubmit,
  showCloseWithComment = false,
  onCloseWithComment,
  initialBody = '',
  bodyRequired,
  bodyLabel,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [body, setBody] = useState('');
  const [issueTitle, setIssueTitle] = useState('');
  const [issueType, setIssueType] = useState('Feature');
  const [selectedLabels, setSelectedLabels] = useState([]);
  const [selectedAssignees, setSelectedAssignees] = useState([]);
  const [availableLabels, setAvailableLabels] = useState([]);
  const [availableAssignees, setAvailableAssignees] = useState([]);
  const [labelsLoading, setLabelsLoading] = useState(false);
  const [assigneesLoading, setAssigneesLoading] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef(null);
  const previewRequestId = useRef(0);
  const isBodyRequired =
    bodyRequired !== undefined ? bodyRequired : mode === 'comment';
  const resolvedBodyLabel =
    bodyLabel || (mode === 'issue' ? 'Description' : 'Comment');

  const resetState = () => {
    setActiveTab(0);
    setBody('');
    setIssueTitle('');
    setIssueType('Feature');
    setSelectedLabels([]);
    setSelectedAssignees([]);
    setPreviewHtml('');
    setPreviewError(null);
    setSubmitError(null);
    setIsSubmitting(false);
  };

  useEffect(() => {
    if (!isOpen) {
      resetState();
      return;
    }
    setActiveTab(0);
    setBody(initialBody || '');
    setIssueTitle('');
    setIssueType('Feature');
    setSelectedLabels([]);
    setSelectedAssignees([]);
    setPreviewHtml('');
    setPreviewError(null);
    setSubmitError(null);
    setIsSubmitting(false);

    if (mode !== 'issue') return;

    // Load labels
    if (labelsCache.data.length > 0) {
      setAvailableLabels(labelsCache.data);
    } else {
      setLabelsLoading(true);
      fetchLabels()
        .then((data) => {
          labelsCache.data = data;
          setAvailableLabels(data);
          setLabelsLoading(false);
        })
        .catch(() => setLabelsLoading(false));
    }

    // Load assignees
    if (assigneesCache.data.length > 0) {
      setAvailableAssignees(assigneesCache.data);
    } else {
      setAssigneesLoading(true);
      fetchAssignees()
        .then((data) => {
          assigneesCache.data = data;
          setAvailableAssignees(data);
          setAssigneesLoading(false);
        })
        .catch(() => setAssigneesLoading(false));
    }
  }, [isOpen, mode, initialBody]);

  useEffect(() => {
    if (!isOpen || activeTab !== 1) return;

    const requestId = ++previewRequestId.current;
    setPreviewLoading(true);
    setPreviewError(null);

    renderMarkdown(body || '')
      .then((data) => {
        if (previewRequestId.current !== requestId) return;
        setPreviewHtml(data.html || '');
        setPreviewLoading(false);
      })
      .catch((err) => {
        if (previewRequestId.current !== requestId) return;
        setPreviewError(err.message);
        setPreviewLoading(false);
      });
  }, [isOpen, activeTab, body]);

  const handleClose = () => {
    if (isSubmitting) return;
    onClose?.();
  };

  const buildIssuePayload = () => ({
    title: issueTitle.trim(),
    body: body || undefined,
    type: issueType || undefined,
    labels: selectedLabels.length > 0 ? selectedLabels : undefined,
    assignees: selectedAssignees.length > 0 ? selectedAssignees : undefined,
  });

  const handleSubmit = async () => {
    if (mode === 'issue' && !issueTitle.trim()) {
      setSubmitError('Title is required');
      return;
    }
    if (isBodyRequired && !body.trim()) {
      setSubmitError('Comment body is required');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      if (mode === 'issue') {
        await onSubmit?.(buildIssuePayload());
      } else {
        await onSubmit?.(body);
      }
      onClose?.();
    } catch (err) {
      setSubmitError(err.message || 'Submit failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseWithComment = async () => {
    if (!body.trim()) {
      setSubmitError('Comment body is required');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await onCloseWithComment?.(body);
      onClose?.();
    } catch (err) {
      setSubmitError(err.message || 'Close with comment failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleLabel = (name, checked) => {
    setSelectedLabels((prev) =>
      checked ? [...prev, name] : prev.filter((n) => n !== name)
    );
  };

  const toggleAssignee = (login, checked) => {
    setSelectedAssignees((prev) =>
      checked ? [...prev, login] : prev.filter((n) => n !== login)
    );
  };

  const actions = [
    <Button
      key="submit"
      variant="primary"
      onClick={handleSubmit}
      isLoading={isSubmitting}
      isDisabled={
        isSubmitting ||
        (mode === 'issue' ? !issueTitle.trim() : isBodyRequired && !body.trim())
      }
    >
      {submitLabel}
    </Button>,
  ];

  if (showCloseWithComment && mode === 'comment') {
    actions.push(
      <Button
        key="close-comment"
        variant="secondary"
        onClick={handleCloseWithComment}
        isLoading={isSubmitting}
        isDisabled={isSubmitting || !body.trim()}
      >
        Close with Comment
      </Button>
    );
  }

  actions.push(
    <Button
      key="cancel"
      variant="link"
      onClick={handleClose}
      isDisabled={isSubmitting}
    >
      Cancel
    </Button>
  );

  return (
    <Modal
      title={title}
      isOpen={isOpen}
      onClose={handleClose}
      actions={actions}
      variant="medium"
    >
      <Form>
        {mode === 'issue' && (
          <>
            <FormGroup label="Title" isRequired fieldId="issue-title">
              <TextInput
                id="issue-title"
                value={issueTitle}
                onChange={(value) => {
                  const stringValue =
                    typeof value === 'string'
                      ? value
                      : value?.target?.value || '';
                  setIssueTitle(stringValue);
                  setSubmitError(null);
                }}
                placeholder="Issue title"
                isRequired
              />
            </FormGroup>
            <FormGroup label="Type" fieldId="issue-type">
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {ISSUE_TYPES.map((typeName) => (
                  <Button
                    key={typeName}
                    variant={issueType === typeName ? 'primary' : 'secondary'}
                    onClick={() => setIssueType(typeName)}
                    style={{
                      padding: '0.25rem 0.75rem',
                      fontSize: '0.875rem',
                    }}
                  >
                    {typeName}
                  </Button>
                ))}
              </div>
            </FormGroup>
            <FormGroup label="Labels" fieldId="issue-labels">
              {labelsLoading ? (
                <Spinner size="sm" />
              ) : (
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    maxHeight: '120px',
                    overflowY: 'auto',
                  }}
                >
                  {availableLabels.map((label) => {
                    const checked = selectedLabels.includes(label.name);
                    return (
                      <Tooltip
                        key={label.id || label.name}
                        content={label.description || ''}
                      >
                        <div>
                          <Checkbox
                            id={`new-issue-label-${label.name}`}
                            isChecked={checked}
                            onChange={(isChecked) =>
                              toggleLabel(label.name, isChecked)
                            }
                            label={
                              <span
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '0.35rem',
                                }}
                              >
                                <span
                                  style={{
                                    display: 'inline-block',
                                    width: '10px',
                                    height: '10px',
                                    borderRadius: '2px',
                                    backgroundColor: `#${label.color}`,
                                  }}
                                />
                                {label.name}
                              </span>
                            }
                          />
                        </div>
                      </Tooltip>
                    );
                  })}
                  {availableLabels.length === 0 && (
                    <span style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                      No labels available
                    </span>
                  )}
                </div>
              )}
            </FormGroup>
            <FormGroup label="Assignees" fieldId="issue-assignees">
              {assigneesLoading ? (
                <Spinner size="sm" />
              ) : (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                    maxHeight: '120px',
                    overflowY: 'auto',
                  }}
                >
                  {availableAssignees.map((assignee) => {
                    const checked = selectedAssignees.includes(assignee.login);
                    return (
                      <Checkbox
                        key={assignee.id || assignee.login}
                        id={`new-issue-assignee-${assignee.login}`}
                        isChecked={checked}
                        onChange={(isChecked) =>
                          toggleAssignee(assignee.login, isChecked)
                        }
                        label={
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.35rem',
                            }}
                          >
                            <UserAvatar user={assignee} size={18} />
                            {assignee.login}
                          </span>
                        }
                      />
                    );
                  })}
                  {availableAssignees.length === 0 && (
                    <span style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                      No assignees available
                    </span>
                  )}
                </div>
              )}
            </FormGroup>
          </>
        )}

        <FormGroup
          label={resolvedBodyLabel}
          fieldId="markdown-body"
          isRequired={isBodyRequired}
        >
          <Tabs
            activeKey={activeTab}
            onSelect={(_e, key) => setActiveTab(key)}
            style={{ marginBottom: '0.5rem' }}
          >
            <Tab eventKey={0} title={<TabTitleText>Edit</TabTitleText>}>
              <TextArea
                id="markdown-body"
                ref={textareaRef}
                value={body}
                onChange={(value) => {
                  const stringValue =
                    typeof value === 'string'
                      ? value
                      : value?.target?.value || '';
                  setBody(stringValue);
                  setSubmitError(null);
                }}
                placeholder="Write markdown…"
                rows={10}
                style={{ fontFamily: 'monospace', minHeight: '200px' }}
              />
            </Tab>
            <Tab eventKey={1} title={<TabTitleText>Preview</TabTitleText>}>
              <div
                style={{
                  minHeight: '200px',
                  padding: '0.75rem',
                  border: '1px solid #d2d2d2',
                  borderRadius: '0.25rem',
                  backgroundColor: '#fff',
                }}
              >
                {previewLoading && (
                  <div style={{ textAlign: 'center', padding: '1rem' }}>
                    <Spinner size="md" />
                  </div>
                )}
                {previewError && (
                  <Alert variant="danger" title="Preview failed" isInline>
                    {previewError}
                  </Alert>
                )}
                {!previewLoading && !previewError && (
                  <div
                    className="markdown-body"
                    dangerouslySetInnerHTML={{
                      __html:
                        previewHtml || '<p><em>Nothing to preview</em></p>',
                    }}
                  />
                )}
              </div>
            </Tab>
          </Tabs>
        </FormGroup>

        {submitError && (
          <Alert variant="danger" title="Error" isInline>
            {submitError}
          </Alert>
        )}
      </Form>
    </Modal>
  );
};

export default MarkdownInputModal;
