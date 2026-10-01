// Generated-by: openai-code-assist
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import LabelColorInput from './LabelColorInput';

describe('LabelColorInput', () => {
  it('toggles between text input and graphical picker', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <LabelColorInput id="label-color" value="336699" onChange={onChange} />
    );

    expect(screen.getByRole('textbox')).toHaveValue('336699');
    expect(
      screen.queryByLabelText('Choose label color')
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('checkbox'));

    expect(screen.getByLabelText('Choose label color')).toHaveValue('#336699');
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('keeps picker changes in the text value when toggled back', async () => {
    const user = userEvent.setup();

    const ControlledColorInput = () => {
      const [color, setColor] = useState('');
      return (
        <LabelColorInput id="label-color" value={color} onChange={setColor} />
      );
    };

    render(<ControlledColorInput />);

    await user.click(screen.getByRole('checkbox'));
    const picker = screen.getByLabelText('Choose label color');
    fireEvent.change(picker, { target: { value: '#abcdef' } });

    expect(picker).toHaveValue('#abcdef');
    await user.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('textbox')).toHaveValue('#abcdef');
  });
});
