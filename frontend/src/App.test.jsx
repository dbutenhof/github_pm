// ai-generated: Cursor
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import App from './App';
import * as api from './services/api';
import { clearMilestonesCache } from './utils/milestonesCache';
import { clearLabelsCache } from './utils/labelsCache';
import assigneesCache from './utils/assigneesCache';

vi.mock('./services/api');

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearMilestonesCache();
    clearLabelsCache();
    // Clear assignees cache
    assigneesCache.data = [];
    assigneesCache.loading = false;
    assigneesCache.error = null;
    assigneesCache.promise = null;
    // Default mock for fetchProject
    api.fetchProject.mockResolvedValue({
      app_name: 'Test App',
      github_repo: 'test/repo',
    });
    // Default mock for fetchLabels (preloaded in background)
    api.fetchLabels.mockResolvedValue([]);
    // Default mock for fetchAssignees (preloaded in background)
    api.fetchAssignees.mockResolvedValue([]);
  });

  afterEach(() => {
    // Clear assignees cache after each test
    assigneesCache.data = [];
    assigneesCache.loading = false;
    assigneesCache.error = null;
    assigneesCache.promise = null;
  });

  it('renders loading state initially', async () => {
    api.fetchMilestones.mockImplementation(() => new Promise(() => {}));
    await act(async () => {
      render(<App />);
    });
    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  it('displays project name and repo in title', async () => {
    api.fetchProject.mockResolvedValue({
      app_name: 'My Project',
      github_repo: 'owner/repository',
    });
    api.fetchMilestones.mockResolvedValue([]);

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(
        screen.getByText('My Project: owner/repository')
      ).toBeInTheDocument();
    });
  });

  it('displays loading text while fetching project', async () => {
    api.fetchProject.mockImplementation(() => new Promise(() => {}));
    api.fetchMilestones.mockResolvedValue([]);

    await act(async () => {
      render(<App />);
    });
    await waitFor(() => {
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  it('displays fallback title when project fetch fails', async () => {
    api.fetchProject.mockRejectedValue(new Error('Failed'));
    api.fetchMilestones.mockResolvedValue([]);

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText('GitHub Project Manager')).toBeInTheDocument();
    });
  });

  it('renders milestones when loaded', async () => {
    const mockMilestones = [
      { number: 1, title: 'Milestone 1', description: 'Desc 1', due_on: null },
      {
        number: 2,
        title: 'Milestone 2',
        description: 'Desc 2',
        due_on: '2025-12-31',
      },
    ];
    api.fetchMilestones.mockResolvedValue(mockMilestones);

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      // Milestones appear in both chiclets and cards, so use getAllByText
      const milestone1Elements = screen.getAllByText('Milestone 1');
      const milestone2Elements = screen.getAllByText('Milestone 2');
      expect(milestone1Elements.length).toBeGreaterThan(0);
      expect(milestone2Elements.length).toBeGreaterThan(0);
    });
  });

  it('renders error message on fetch failure', async () => {
    api.fetchMilestones.mockRejectedValue(new Error('Network error'));

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText(/Error loading milestones/i)).toBeInTheDocument();
    });
  });

  it('renders empty state when no milestones', async () => {
    api.fetchMilestones.mockResolvedValue([]);

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText(/No milestones found/i)).toBeInTheDocument();
    });
  });
});
