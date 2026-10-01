// Generated-by: openai-code-assist
import React, { useState } from 'react';
import { Switch, TextInput } from '@patternfly/react-core';

const toPickerValue = (value) => {
  const color = String(value || '')
    .trim()
    .replace(/^#/, '');
  if (/^[0-9a-f]{6}$/i.test(color)) {
    return `#${color}`;
  }
  if (/^[0-9a-f]{3}$/i.test(color)) {
    return `#${color
      .split('')
      .map((character) => `${character}${character}`)
      .join('')}`;
  }
  return '#000000';
};

const readTextValue = (event, value) =>
  typeof value === 'string' ? value : event?.target?.value || '';

const LabelColorInput = ({ id, value = '', onChange }) => {
  const [isPickerEnabled, setIsPickerEnabled] = useState(false);

  return (
    <div>
      <Switch
        id={`${id}-picker-toggle`}
        label="Color picker"
        labelOff="Text input"
        isChecked={isPickerEnabled}
        onChange={(_event, checked) => setIsPickerEnabled(checked)}
      />
      {isPickerEnabled ? (
        <input
          id={id}
          type="color"
          value={toPickerValue(value)}
          onChange={(event) => onChange(event.target.value)}
          aria-label="Choose label color"
          style={{
            display: 'block',
            width: '4rem',
            height: '2.5rem',
            marginTop: '0.5rem',
            padding: '0.125rem',
          }}
        />
      ) : (
        <TextInput
          id={id}
          value={value}
          onChange={(event, nextValue) =>
            onChange(readTextValue(event, nextValue))
          }
          placeholder="Enter hex color (e.g., ffffff)"
        />
      )}
    </div>
  );
};

export default LabelColorInput;
