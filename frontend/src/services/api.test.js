// Generated-by: Cursor
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchMilestones,
  fetchIssues,
  fetchComments,
  fetchProject,
  fetchSdlcDelivery,
  fetchEscapedDefectRate,
  fetchBugBacklogDelta,
  fetchProjectStatusReport,
  setIssueParent,
  clearIssueParent,
  adoptParentMilestone,
  addBlockedBy,
  removeBlockedBy,
  addBlocking,
  removeBlocking,
  createComment,
  closeIssueWithComment,
  renderMarkdown,
  createIssue,
  updateComment,
  updateIssueBody,
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
      const mockPayload = {
        issues: [{ id: 1, number: 459, title: 'Test Issue' }],
        pull_requests: [{ id: 2, number: 460, title: 'Test PR' }],
      };
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockPayload,
      });

      const result = await fetchIssues(6);
      expect(result).toEqual(mockPayload);
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

  describe('fetchSdlcDelivery', () => {
    it('requests delivery metrics with default weeks', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ weeks: 4, week_days: 7, slices: [] }),
      });
      const result = await fetchSdlcDelivery();
      expect(result.weeks).toBe(4);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/sdlc/delivery?weeks=4&week_days=7'
      );
    });

    it('throws on failure', async () => {
      global.fetch.mockResolvedValue({ ok: false, statusText: 'Bad Gateway' });
      await expect(fetchSdlcDelivery(8)).rejects.toThrow(
        'Failed to fetch SDLC delivery metrics'
      );
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/sdlc/delivery?weeks=8&week_days=7'
      );
    });
  });

  describe('fetchEscapedDefectRate', () => {
    it('fetches escaped defect rate', async () => {
      const body = { weeks: 4, week_days: 7, slices: [] };
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => body,
      });
      const result = await fetchEscapedDefectRate();
      expect(result).toEqual(body);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/sdlc/escaped-defect-rate?weeks=4&week_days=7'
      );
    });
  });

  describe('fetchBugBacklogDelta', () => {
    it('requests bug backlog delta', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ weeks: 4, slices: [] }),
      });
      await fetchBugBacklogDelta();
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/sdlc/bug-backlog-delta?weeks=4&week_days=7'
      );
    });
  });

  describe('fetchProjectStatusReport', () => {
    it('requests report with start_date and end_date', async () => {
      const body = {
        start_date: '2025-04-04',
        end_date: '2025-04-10',
        merged_pull_requests: [],
        opened_pull_requests: [],
        opened_issues: [],
        recently_updated_pull_requests: [],
        reviewer_attention_needed: [],
        creator_attention_needed: [],
        pr_backlog: [],
      };
      global.fetch.mockResolvedValue({ ok: true, json: async () => body });
      const result = await fetchProjectStatusReport('2025-04-04', '2025-04-10');
      expect(result).toEqual(body);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/project-status?start_date=2025-04-04&end_date=2025-04-10'
      );
    });

    it('requests report without query when both dates omitted', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          start_date: '2025-01-01',
          end_date: '2025-01-07',
          merged_pull_requests: [],
          opened_pull_requests: [],
          opened_issues: [],
          recently_updated_pull_requests: [],
          reviewer_attention_needed: [],
          creator_attention_needed: [],
          pr_backlog: [],
        }),
      });
      await fetchProjectStatusReport('', '');
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/project-status');
    });

    it('throws on failure', async () => {
      global.fetch.mockResolvedValue({ ok: false, statusText: 'Bad Gateway' });
      await expect(
        fetchProjectStatusReport('2025-04-04', '2025-04-10')
      ).rejects.toThrow('Failed to fetch project status report');
    });
  });

  describe('hierarchy APIs', () => {
    it('setIssueParent PUTs parent_number', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ parent_number: 10 }),
      });
      await setIssueParent(20, 10);
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/issues/20/parent', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_number: 10 }),
      });
    });

    it('clearIssueParent DELETEs parent', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ message: 'parent cleared' }),
      });
      await clearIssueParent(20);
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/issues/20/parent', {
        method: 'DELETE',
      });
    });

    it('adoptParentMilestone POSTs', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ to_milestone: 2 }),
      });
      await adoptParentMilestone(20);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/issues/20/adopt-parent-milestone',
        { method: 'POST' }
      );
    });
  });

  describe('dependency APIs', () => {
    it('addBlockedBy POSTs issue_number', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ relationship: 'blocked_by' }),
      });
      await addBlockedBy(1, 17);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/issues/1/dependencies/blocked_by',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ issue_number: 17 }),
        }
      );
    });

    it('removeBlockedBy DELETEs by blocking issue number', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ message: 'blocked_by removed' }),
      });
      await removeBlockedBy(1, 17);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/issues/1/dependencies/blocked_by/17',
        { method: 'DELETE' }
      );
    });

    it('addBlocking POSTs issue_number', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ relationship: 'blocking' }),
      });
      await addBlocking(1, 88);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/issues/1/dependencies/blocking',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ issue_number: 88 }),
        }
      );
    });

    it('removeBlocking DELETEs by blocked issue number', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ message: 'blocking removed' }),
      });
      await removeBlocking(1, 88);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/issues/1/dependencies/blocking/88',
        { method: 'DELETE' }
      );
    });
  });

  describe('comment and issue write APIs', () => {
    it('createComment POSTs body', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ id: 1, body: 'Hi' }),
      });
      await createComment(42, 'Hi');
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/comments/42', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: 'Hi' }),
      });
    });

    it('updateComment PATCHes body', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ id: 99, body: 'Updated' }),
      });
      await updateComment(99, 'Updated');
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/comments/99/body', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: 'Updated' }),
      });
    });

    it('updateIssueBody PATCHes body', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ number: 42, body: 'New desc' }),
      });
      await updateIssueBody(42, 'New desc');
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/issues/42/body', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: 'New desc' }),
      });
    });

    it('closeIssueWithComment POSTs body', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ comment: {}, issue: { state: 'closed' } }),
      });
      await closeIssueWithComment(42, 'Done');
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/issues/42/close-with-comment',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ body: 'Done' }),
        }
      );
    });

    it('renderMarkdown POSTs text', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ html: '<p>x</p>' }),
      });
      const result = await renderMarkdown('**x**');
      expect(result).toEqual({ html: '<p>x</p>' });
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/markdown', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: '**x**' }),
      });
    });

    it('createIssue POSTs issue payload', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ number: 99, title: 'New' }),
      });
      await createIssue({
        title: 'New',
        body: 'Body',
        type: 'Bug',
        labels: ['bug'],
        assignees: ['alice'],
        milestone: 6,
      });
      expect(global.fetch).toHaveBeenCalledWith('/api/v1/issues', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'New',
          body: 'Body',
          type: 'Bug',
          labels: ['bug'],
          assignees: ['alice'],
          milestone: 6,
        }),
      });
    });

    it('throws on createComment failure', async () => {
      global.fetch.mockResolvedValue({ ok: false, statusText: 'Forbidden' });
      await expect(createComment(1, 'x')).rejects.toThrow(
        'Failed to create comment'
      );
    });
  });
});
