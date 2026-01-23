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
  // Mock localStorage
  let store = {};
  const localStorageMock = {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage mock store
    store = {};
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
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

  it('loads sort order from localStorage on mount', async () => {
    const savedSortOrder = ['label1', 'label2', 'label3'];
    localStorageMock.setItem(
      'issueSortOrder',
      JSON.stringify(savedSortOrder)
    );
    api.fetchMilestones.mockResolvedValue([]);

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      // Verify localStorage.getItem was called
      expect(localStorageMock.getItem).toHaveBeenCalledWith('issueSortOrder');
    });
  });

  it('saves sort order to localStorage when changed', async () => {
    api.fetchMilestones.mockResolvedValue([]);
    api.fetchLabels.mockResolvedValue([
      { name: 'label1', color: 'ff0000', description: 'Label 1' },
      { name: 'label2', color: '00ff00', description: 'Label 2' },
    ]);

    await act(async () => {
      render(<App />);
    });

    await waitFor(() => {
      expect(screen.getByText('Sort')).toBeInTheDocument();
    });

    // Open the Sort modal
    const sortButton = screen.getByText('Sort');
    await act(async () => {
      sortButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText(/Sort Issues by Labels/i)).toBeInTheDocument();
    });

    // Add a label to the sort order
    const addLabelButton = screen.getByText('+ label1');
    await act(async () => {
      addLabelButton.click();
    });

    // Verify localStorage.setItem was called with the new sort order
    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'issueSortOrder',
        JSON.stringify(['label1'])
      );
    });
  });
});
