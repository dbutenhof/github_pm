// Generated-by: Cline
import React, { useEffect, useRef, useState } from 'react';
import { Button, Popover, Spinner, Tooltip } from '@patternfly/react-core';
import {
  BugIcon,
  CaretDownIcon,
  CatalogIcon,
  LayerGroupIcon,
  OutlinedQuestionCircleIcon,
  RocketIcon,
  TaskIcon,
} from '@patternfly/react-icons';
import { updateIssueType } from '../services/api';
import { getIssueSubIssueCount, getIssueTypeKind } from '../utils/issueType';

const TYPE_PRESENTATION = {
  epic: { Icon: LayerGroupIcon, label: 'Epic', color: '#6a3d9a' },
  bug: { Icon: BugIcon, label: 'Bug', color: '#c9190b' },
  feature: { Icon: RocketIcon, label: 'Feature', color: '#0066cc' },
  task: { Icon: TaskIcon, label: 'Task', color: '#3d7317' },
  custom: { Icon: CatalogIcon, label: null, color: '#6a6e73' },
  untyped: {
    Icon: OutlinedQuestionCircleIcon,
    label: 'No issue type',
    color: '#6a6e73',
  },
};

// Epic intentionally has no menu entry: it is derived from sub-issues.
const TYPE_OPTIONS = [
  TYPE_PRESENTATION.bug,
  TYPE_PRESENTATION.feature,
  TYPE_PRESENTATION.task,
];

const menuStyle = {
  position: 'absolute',
  top: '100%',
  left: '0',
  marginTop: '0.25rem',
  backgroundColor: '#fff',
  border: '1px solid #d2d2d2',
  borderRadius: '0.25rem',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
  zIndex: 1000,
  minWidth: '9rem',
};

const menuItemStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '0.5rem',
  width: '100%',
  padding: '0.45rem 0.6rem',
  border: 0,
  background: 'transparent',
  cursor: 'pointer',
  fontSize: '0.875rem',
  textAlign: 'left',
};

const presentationFor = (issue, typeKind) => {
  const presentation = TYPE_PRESENTATION[typeKind] || TYPE_PRESENTATION.untyped;
  if (typeKind !== 'custom') return presentation;
  return {
    ...presentation,
    label: String(issue.type?.name || '').trim() || 'Other',
  };
};

/**
 * Editable issue type control used by the Planning board Type column.
 *
 * Epic is not selectable: it is derived from whether the issue has sub-issues.
 *
 * Generated-by: Cline
 */
const IssueTypeSelect = ({ issue, onChanged }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isEpicNoticeOpen, setIsEpicNoticeOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const toggleRef = useRef(null);
  const menuRef = useRef(null);

  const typeKind = getIssueTypeKind(issue);
  const presentation = presentationFor(issue, typeKind);
  const label = presentation.label;
  const TypeIcon = presentation.Icon;
  const isEpic = typeKind === 'epic';
  const currentName = String(issue.type?.name || '')
    .trim()
    .toLowerCase();
  const subIssueCount = getIssueSubIssueCount(issue);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handlePointerDown = (event) => {
      if (
        toggleRef.current?.contains(event.target) ||
        menuRef.current?.contains(event.target)
      ) {
        return;
      }
      setIsOpen(false);
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = async (nextName) => {
    setIsOpen(false);
    setError(null);
    if (nextName.toLowerCase() === currentName) return;
    setBusy(true);
    try {
      const updated = await updateIssueType(issue.number, nextName);
      const nextType = updated?.type || {
        ...(issue.type || {}),
        name: nextName,
      };
      onChanged?.({ ...issue, ...updated, type: nextType });
    } catch (err) {
      setError(err?.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  const trigger = (
    <Button
      variant="plain"
      isDisabled={busy}
      aria-label={
        isEpic
          ? 'Epic (based on sub-issues)'
          : typeKind === 'untyped'
            ? `Set issue type for #${issue.number}`
            : `Change issue type for #${issue.number} (currently ${label})`
      }
      aria-haspopup={isEpic ? undefined : 'menu'}
      aria-expanded={isEpic ? undefined : isOpen}
      data-type-kind={typeKind}
      title={label}
      onClick={() => {
        if (isEpic) {
          setIsEpicNoticeOpen((open) => !open);
        } else {
          setIsOpen((open) => !open);
          setError(null);
        }
      }}
      style={{ padding: '0.125rem', minWidth: 'auto' }}
    >
      {busy ? (
        <Spinner
          size="sm"
          aria-label={`Updating type for issue #${issue.number}`}
        />
      ) : (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.2rem',
          }}
        >
          <TypeIcon style={{ fontSize: '1rem', color: presentation.color }} />
          {!isEpic && <CaretDownIcon style={{ fontSize: '0.6rem' }} />}
        </span>
      )}
    </Button>
  );

  const tooltip =
    typeKind === 'untyped'
      ? 'Set issue type'
      : issue.type?.description || label;

  return (
    <div
      ref={toggleRef}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      {isEpic ? (
        <Popover
          aria-label={`Epic type for #${issue.number}`}
          alertSeverityVariant="info"
          alertSeverityScreenReaderText="Information"
          headerContent="Epic is based on sub-issues"
          bodyContent={`This issue has ${subIssueCount} sub-issue${
            subIssueCount === 1 ? '' : 's'
          }. Add or remove sub-issues to change this icon; Epic cannot be selected directly.`}
          isVisible={isEpicNoticeOpen}
          shouldClose={() => setIsEpicNoticeOpen(false)}
          position="right"
        >
          {trigger}
        </Popover>
      ) : (
        <Tooltip content={tooltip}>{trigger}</Tooltip>
      )}
      {!isEpic && isOpen && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Issue type options for #${issue.number}`}
          style={menuStyle}
        >
          {TYPE_OPTIONS.map((option) => {
            const OptionIcon = option.Icon;
            const isCurrent = currentName === option.label.toLowerCase();
            return (
              <button
                type="button"
                role="menuitem"
                key={option.label}
                onClick={() => handleSelect(option.label)}
                style={menuItemStyle}
              >
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  <OptionIcon
                    aria-hidden="true"
                    style={{ fontSize: '0.875rem', color: option.color }}
                  />
                  {option.label}
                </span>
                {isCurrent && <span aria-hidden="true">✓</span>}
              </button>
            );
          })}
        </div>
      )}
      {error && (
        <div
          role="alert"
          style={{
            color: '#c9190b',
            fontSize: '0.7rem',
            maxWidth: '12rem',
            marginTop: '0.25rem',
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

export default IssueTypeSelect;
