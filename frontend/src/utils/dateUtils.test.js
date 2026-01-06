// ai-generated: Cursor
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getDaysSince, formatDate } from './dateUtils';

describe('dateUtils', () => {
  beforeEach(() => {
    // Mock current date to 2025-12-15
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-12-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('getDaysSince', () => {
    it('calculates days since a date', () => {
      const dateString = '2025-12-10T12:00:00Z';
      expect(getDaysSince(dateString)).toBe(5);
    });

    it('returns 0 for null or undefined', () => {
      expect(getDaysSince(null)).toBe(0);
      expect(getDaysSince(undefined)).toBe(0);
    });

    it('handles dates in the future', () => {
      const dateString = '2025-12-20T12:00:00Z';
      expect(getDaysSince(dateString)).toBe(5);
    });

    it('handles same day', () => {
      const dateString = '2025-12-15T00:00:00Z';
      expect(getDaysSince(dateString)).toBe(0);
    });
  });

  describe('formatDate', () => {
    it('formats a date string', () => {
      const dateString = '2025-12-15T12:00:00Z';
      const formatted = formatDate(dateString);
      expect(formatted).toMatch(/December/);
      expect(formatted).toMatch(/15/);
      expect(formatted).toMatch(/2025/);
    });

    it('returns "No date" for null or undefined', () => {
      expect(formatDate(null)).toBe('No date');
      expect(formatDate(undefined)).toBe('No date');
    });
  });
});
