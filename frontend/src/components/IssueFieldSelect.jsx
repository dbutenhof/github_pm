// Generated-by: Cline
import React, { useEffect, useRef, useState } from 'react';
import { Button, Spinner } from '@patternfly/react-core';
import { CaretDownIcon } from '@patternfly/react-icons';
import { setIssueFieldValue } from '../services/api';
import {
  issueFieldOptionColor,
  issueFieldValueLabel,
} from '../utils/issueFields';

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
  minWidth: '10rem',
  maxHeight: '20rem',
  overflowY: 'auto',
};

const menuItemStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '0.5rem',
  width: '100%',
  padding: '0.5rem',
  border: 0,
  background: 'transparent',
  cursor: 'pointer',
  fontSize: '0.875rem',
  textAlign: 'left',
};

const colorDotStyle = (color) => ({
  width: '0.5rem',
  height: '0.5rem',
  borderRadius: '50%',
  backgroundColor: issueFieldOptionColor(color),
  flexShrink: 0,
});

/**
 * Editable single-select issue field control used by Planning board rows.
 *
 * Generated-by: Cline
 */
const IssueFieldSelect = ({ field, value, issueNumber, onChanged }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const toggleRef = useRef(null);
  const menuRef = useRef(null);

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

  const currentOptionId = value?.option_id ?? null;
  const options = field.options || [];
  const label = issueFieldValueLabel(value);

  const handleSelect = async (optionId) => {
    setIsOpen(false);
    setError(null);
    if ((optionId ?? null) === currentOptionId) return;
    setBusy(true);
    try {
      const result = await setIssueFieldValue(issueNumber, field.id, optionId);
      onChanged?.(result?.issue_field_values || []);
    } catch (err) {
      setError(err?.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      ref={toggleRef}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      <Button
        variant={value ? 'primary' : 'secondary'}
        isDisabled={busy}
        aria-label={`Change ${field.name} for issue #${issueNumber}`}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => {
          setIsOpen((open) => !open);
          setError(null);
        }}
        style={{
          padding: '0.25rem 0.75rem',
          fontSize: '0.75rem',
          minWidth: 'auto',
        }}
      >
        {busy ? (
          <Spinner size="sm" aria-label={`Updating ${field.name}`} />
        ) : (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            {value?.color && (
              <span aria-hidden="true" style={colorDotStyle(value.color)} />
            )}
            <span style={{ color: value ? undefined : '#6a6e73' }}>
              {value ? label : 'Not set'}
            </span>
            <CaretDownIcon style={{ fontSize: '0.65rem' }} />
          </span>
        )}
      </Button>
      {isOpen && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`${field.name} options for issue #${issueNumber}`}
          style={menuStyle}
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => handleSelect(null)}
            style={menuItemStyle}
          >
            <span style={{ color: '#6a6e73', fontStyle: 'italic' }}>
              No value
            </span>
            {currentOptionId === null && <span aria-hidden="true">✓</span>}
          </button>
          {options.map((option) => (
            <button
              type="button"
              role="menuitem"
              key={option.id}
              onClick={() => handleSelect(option.id)}
              style={menuItemStyle}
            >
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <span aria-hidden="true" style={colorDotStyle(option.color)} />
                {option.name}
              </span>
              {currentOptionId === option.id && (
                <span aria-hidden="true">✓</span>
              )}
            </button>
          ))}
          {options.length === 0 && (
            <div style={{ padding: '0.5rem', color: '#6a6e73' }}>
              No options
            </div>
          )}
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

export default IssueFieldSelect;
