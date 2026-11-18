// Generated-by: Codex
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useReactions } from './useReactions';

describe('reaction loading', () => {
  it('loads issue users only when the description opens', async () => {
    const data = [
      { content: '+1', user: { login: 'alice' } },
      { content: 'heart', user: null },
    ];
    const loader = vi.fn().mockResolvedValue(data);
    const { result, rerender } = renderHook(
      ({ active }) => useReactions(1, 2, active, loader),
      { initialProps: { active: false } }
    );
    expect(loader).not.toHaveBeenCalled();
    rerender({ active: true });
    await waitFor(() => expect(result.current.data).toEqual(data));
    expect(loader).toHaveBeenCalledTimes(1);
  });

  it.each(['empty', 'failure'])(
    'finishes a %s attempt without a render-driven retry loop',
    async (outcome) => {
      const loader =
        outcome === 'empty'
          ? vi.fn().mockResolvedValue([])
          : vi.fn().mockRejectedValue(new Error('failed'));
      const { result, rerender } = renderHook(
        ({ active }) => useReactions(1, 1, active, loader),
        { initialProps: { active: true } }
      );
      await waitFor(() => expect(result.current.loading).toBe(false));
      rerender({ active: true });
      expect(loader).toHaveBeenCalledTimes(1);
      expect(result.current.data).toEqual([]);
      if (outcome === 'failure') expect(result.current.error).toBe('failed');
      rerender({ active: false });
      rerender({ active: true });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(loader).toHaveBeenCalledTimes(2);
    }
  );

  it('uses batched comment reactions without a per-comment request', () => {
    const loader = vi.fn();
    const data = [{ content: 'eyes', user: { login: 'reviewer' } }];
    const { result } = renderHook(() => useReactions(1, 1, true, loader, data));
    expect(result.current.data).toEqual(data);
    expect(loader).not.toHaveBeenCalled();
  });
});
