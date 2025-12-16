import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchMilestones,
  fetchIssues,
  fetchComments,
  fetchProject,
} from './api';

describe('api', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  describe('fetchMilestones', () => {
    it('fetches milestones successfully', async () => {
      const mockMilestones = [
        { number: 1, title: 'Milestone 1', description: '', due_on: null },
      ];
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockMilestones,
      });

      const result = await fetchMilestones();
      expect(result).toEqual(mockMilestones);
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/milestones');
    });

    it('throws error on failed fetch', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(fetchMilestones()).rejects.toThrow(
        'Failed to fetch milestones'
      );
    });
  });

  describe('fetchIssues', () => {
    it('fetches issues successfully', async () => {
      const mockIssues = [{ id: 1, number: 459, title: 'Test Issue' }];
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockIssues,
      });

      const result = await fetchIssues(6);
      expect(result).toEqual(mockIssues);
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/issues/6');
    });

    it('throws error on failed fetch', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      });

      await expect(fetchIssues(6)).rejects.toThrow('Failed to fetch issues');
    });
  });

  describe('fetchComments', () => {
    it('fetches comments successfully', async () => {
      const mockComments = [
        { id: 1, body: 'Test comment', user: { login: 'testuser' } },
      ];
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockComments,
      });

      const result = await fetchComments(459);
      expect(result).toEqual(mockComments);
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/comments/459');
    });

    it('throws error on failed fetch', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(fetchComments(459)).rejects.toThrow(
        'Failed to fetch comments'
      );
    });
  });

  describe('fetchProject', () => {
    it('fetches project successfully', async () => {
      const mockProject = {
        app_name: 'My App',
        github_repo: 'owner/repo',
      };
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockProject,
      });

      const result = await fetchProject();
      expect(result).toEqual(mockProject);
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/project');
    });

    it('throws error on failed fetch', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        statusText: 'Not Found',
      });

      await expect(fetchProject()).rejects.toThrow('Failed to fetch project');
    });
  });
});
