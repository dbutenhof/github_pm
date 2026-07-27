// Generated-by: Cursor
// Assisted-by: Cursor
import React, { useState, useEffect } from 'react';
import {
  Page,
  PageSection,
  Title,
  Spinner,
  Alert,
  Bullseye,
  Button,
  Tabs,
  Tab,
  TabTitleText,
} from '@patternfly/react-core';
import {
  fetchMilestones,
  fetchProject,
  fetchLabels,
  fetchAssignees,
} from './services/api';
import MilestoneCard from './components/MilestoneCard';
import PlanningBoard from './components/PlanningBoard';
import { PlanningDnDProvider } from './components/PlanningDnDContext';
import SdlcKpisPanel from './components/SdlcKpisPanel';
import ProjectStatusPanel from './components/ProjectStatusPanel';
import ManageMilestones from './components/ManageMilestones';
import ManageLabels from './components/ManageLabels';
import ManageSort from './components/ManageSort';
import milestonesCache from './utils/milestonesCache';
import labelsCache, { clearLabelsCache } from './utils/labelsCache';
import assigneesCache from './utils/assigneesCache';
import iconImage from './assets/icon.png';
import './icon.css';

const MAIN_VIEW_TAB_STORAGE_KEY = 'pmStatsMainViewTab';
const VALID_MAIN_VIEW_TABS = new Set(['planning', 'sdlc', 'project-status']);

const App = () => {
  // Initialize with cached data if available
  const [milestones, setMilestones] = useState(milestonesCache.data || []);
  const [loading, setLoading] = useState(milestonesCache.data.length === 0);
  const [error, setError] = useState(milestonesCache.error || null);
  const [project, setProject] = useState(null);
  const [projectLoading, setProjectLoading] = useState(true);
  const [isManageMilestonesOpen, setIsManageMilestonesOpen] = useState(false);
  const [isManageLabelsOpen, setIsManageLabelsOpen] = useState(false);
  const [isManageSortOpen, setIsManageSortOpen] = useState(false);
  const [activeViewTab, setActiveViewTab] = useState(() => {
    try {
      const saved = localStorage.getItem(MAIN_VIEW_TAB_STORAGE_KEY);
      if (saved && VALID_MAIN_VIEW_TABS.has(saved)) {
        return saved;
      }
    } catch (error) {
      console.error('Failed to load main view tab from localStorage:', error);
    }
    return 'planning';
  });

  // Load sort order from localStorage on mount
  const [sortOrder, setSortOrder] = useState(() => {
    try {
      const saved = localStorage.getItem('issueSortOrder');
      return saved ? JSON.parse(saved) : [];
    } catch (error) {
      console.error('Failed to load sort order from localStorage:', error);
      return [];
    }
  });

  const [issueMilestoneRefresh, setIssueMilestoneRefresh] = useState({
    key: 0,
    milestoneNumbers: [],
  });
  // Milestone numbers whose issue/PR lists may be stale after local edits.
  const [dirtyMilestoneNumbers, setDirtyMilestoneNumbers] = useState([]);
  const [hierarchyAction, setHierarchyAction] = useState(null);

  const markMilestonesDirty = (numbers) => {
    const normalized = numbers
      .map((n) => (n == null ? 0 : n))
      .filter((n) => typeof n === 'number');
    if (normalized.length === 0) return;
    setDirtyMilestoneNumbers((prev) => [...new Set([...prev, ...normalized])]);
  };

  const handleHierarchyChanged = (action) => {
    setHierarchyAction({ ...action, key: Date.now() });
    if (action.type === 'relink') {
      markMilestonesDirty([
        action.sourceMilestoneNumber,
        action.targetMilestoneNumber,
        action.fromMilestone,
        action.toMilestone,
      ]);
    } else if (action.type === 'unlink') {
      markMilestonesDirty([action.sourceMilestoneNumber]);
    } else if (action.type === 'error') {
      markMilestonesDirty([
        action.sourceMilestoneNumber,
        action.targetMilestoneNumber,
      ]);
    }
  };

  // MilestoneCards apply hierarchyAction in their effects (children run first).
  // Clear afterward so a remount / later hasLoadedOnce transition cannot
  // re-apply a stale optimistic mutation and duplicate issues.
  useEffect(() => {
    if (hierarchyAction == null) return;
    setHierarchyAction(null);
  }, [hierarchyAction]);

  useEffect(() => {
    fetchProject()
      .then((data) => {
        setProject(data);
        setProjectLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch project:', err);
        setProjectLoading(false);
      });
  }, []);

  // Preload milestones and labels in the background
  useEffect(() => {
    // Preload milestones
    if (
      !milestonesCache.loading &&
      milestonesCache.data.length === 0 &&
      !milestonesCache.promise
    ) {
      milestonesCache.loading = true;
      milestonesCache.error = null;
      milestonesCache.promise = fetchMilestones()
        .then((data) => {
          milestonesCache.data = data;
          milestonesCache.loading = false;
          milestonesCache.error = null;
          milestonesCache.promise = null;
          // Update state if we're still on the page
          setMilestones(data);
          setLoading(false);
        })
        .catch((err) => {
          milestonesCache.loading = false;
          milestonesCache.error = err.message;
          milestonesCache.promise = null;
          setError(err.message);
          setLoading(false);
        });
    } else if (milestonesCache.data.length > 0) {
      // Use cached data immediately
      setMilestones(milestonesCache.data);
      setLoading(false);
      setError(milestonesCache.error);
    } else if (milestonesCache.promise) {
      // Wait for existing promise
      setLoading(true);
      milestonesCache.promise
        .then(() => {
          setMilestones(milestonesCache.data);
          setLoading(false);
          setError(milestonesCache.error);
        })
        .catch(() => {
          setLoading(false);
          setError(milestonesCache.error);
        });
    }

    // Preload labels
    if (
      !labelsCache.loading &&
      labelsCache.data.length === 0 &&
      !labelsCache.promise
    ) {
      labelsCache.loading = true;
      labelsCache.error = null;
      labelsCache.promise = fetchLabels()
        .then((data) => {
          labelsCache.data = data;
          labelsCache.loading = false;
          labelsCache.error = null;
          labelsCache.promise = null;
        })
        .catch((err) => {
          labelsCache.loading = false;
          labelsCache.error = err.message;
          labelsCache.promise = null;
        });
    }

    // Preload assignees
    if (
      !assigneesCache.loading &&
      assigneesCache.data.length === 0 &&
      !assigneesCache.promise
    ) {
      assigneesCache.loading = true;
      assigneesCache.error = null;
      assigneesCache.promise = fetchAssignees()
        .then((data) => {
          assigneesCache.data = data;
          assigneesCache.loading = false;
          assigneesCache.error = null;
          assigneesCache.promise = null;
        })
        .catch((err) => {
          assigneesCache.loading = false;
          assigneesCache.error = err.message;
          assigneesCache.promise = null;
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Save sort order to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem('issueSortOrder', JSON.stringify(sortOrder));
    } catch (error) {
      console.error('Failed to save sort order to localStorage:', error);
    }
  }, [sortOrder]);

  useEffect(() => {
    try {
      localStorage.setItem(MAIN_VIEW_TAB_STORAGE_KEY, activeViewTab);
    } catch (error) {
      console.error('Failed to save main view tab to localStorage:', error);
    }
    if (activeViewTab !== 'planning') {
      setHierarchyAction(null);
    }
  }, [activeViewTab]);

  const loadMilestones = () => {
    setLoading(true);
    setError(null);
    fetchMilestones()
      .then((data) => {
        milestonesCache.data = data;
        milestonesCache.loading = false;
        milestonesCache.error = null;
        setMilestones(data);
        setLoading(false);
      })
      .catch((err) => {
        milestonesCache.loading = false;
        milestonesCache.error = err.message;
        setError(err.message);
        setLoading(false);
      });
  };

  const handleMilestoneChange = () => {
    // Use cached data if available, otherwise load
    if (milestonesCache.data.length > 0) {
      setMilestones(milestonesCache.data);
      setLoading(false);
      setError(milestonesCache.error);
    } else {
      loadMilestones();
    }
  };

  const handleIssueMilestoneMoved = ({
    fromMilestoneNumber,
    toMilestoneNumber,
  }) => {
    markMilestonesDirty([fromMilestoneNumber, toMilestoneNumber]);
  };

  const handleIssueLabelsChanged = ({ milestoneNumber }) => {
    markMilestonesDirty([milestoneNumber]);
  };

  const handleRefreshDirtyMilestones = () => {
    if (dirtyMilestoneNumbers.length === 0) return;
    setIssueMilestoneRefresh((s) => ({
      key: s.key + 1,
      milestoneNumbers: [...dirtyMilestoneNumbers],
    }));
    setDirtyMilestoneNumbers([]);
  };

  const handleLabelChange = () => {
    // Labels are cached in IssueCard, so we don't need to do anything here
    // but we can add a callback if needed in the future
  };

  const renderPlanningContent = () => (
    <PlanningDnDProvider
      milestones={milestones}
      onHierarchyChanged={handleHierarchyChanged}
    >
      {loading && (
        <Bullseye>
          <Spinner size="xl" />
        </Bullseye>
      )}

      {error && (
        <Alert variant="danger" title="Error loading milestones">
          {error}
        </Alert>
      )}

      {!loading && !error && (
        <PlanningBoard>
          {milestones.length === 0 && (
            <Alert variant="info" title="No milestones found">
              There are no milestones available.
            </Alert>
          )}
          {milestones.length > 0 &&
            milestones.map((milestone) => (
              <MilestoneCard
                key={milestone.number}
                milestone={milestone}
                sortOrder={sortOrder}
                issueMilestoneRefresh={issueMilestoneRefresh}
                hierarchyAction={hierarchyAction}
                onIssueMilestoneMoved={handleIssueMilestoneMoved}
                onIssueLabelsChanged={handleIssueLabelsChanged}
              />
            ))}
        </PlanningBoard>
      )}
    </PlanningDnDProvider>
  );

  return (
    <Page className="app-page">
      <PageSection
        className="app-page-chrome"
        variant="light"
        stickyOnBreakpoint={{ default: 'top' }}
        hasShadowBottom
      >
        <div
          className="app-page-header"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}
        >
          <div
            className="app-header-icon-container"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
            }}
          >
            <img
              src={iconImage}
              alt="Application icon"
              className="app-icon"
              style={{
                height: '100px',
                width: 'auto',
                display: 'block',
              }}
            />
            <Title headingLevel="h1" size="2xl">
              {projectLoading
                ? 'Loading...'
                : project
                  ? `${project.app_name}: ${project.github_repo}`
                  : 'GitHub Project Manager'}
            </Title>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button
              variant="secondary"
              onClick={handleRefreshDirtyMilestones}
              isDisabled={dirtyMilestoneNumbers.length === 0}
            >
              {dirtyMilestoneNumbers.length > 0
                ? `Refresh (${dirtyMilestoneNumbers.length})`
                : 'Refresh'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setIsManageMilestonesOpen(true)}
            >
              Manage Milestones
            </Button>
            <Button
              variant="secondary"
              onClick={() => setIsManageLabelsOpen(true)}
            >
              Manage Labels
            </Button>
            <Button
              variant="secondary"
              onClick={() => setIsManageSortOpen(true)}
            >
              Sort
            </Button>
          </div>
        </div>
        <Tabs
          activeKey={activeViewTab}
          onSelect={(_event, key) => setActiveViewTab(key)}
          aria-label="Main views"
        >
          <Tab
            eventKey="planning"
            title={<TabTitleText>Planning</TabTitleText>}
          />
          <Tab eventKey="sdlc" title={<TabTitleText>SDLC</TabTitleText>} />
          <Tab
            eventKey="project-status"
            title={<TabTitleText>Project status</TabTitleText>}
          />
        </Tabs>
      </PageSection>
      <PageSection
        className="app-page-content"
        aria-label="Selected view content"
      >
        {activeViewTab === 'planning' && renderPlanningContent()}
        {activeViewTab === 'sdlc' && <SdlcKpisPanel />}
        {activeViewTab === 'project-status' && <ProjectStatusPanel />}
      </PageSection>
      <ManageMilestones
        isOpen={isManageMilestonesOpen}
        onClose={() => setIsManageMilestonesOpen(false)}
        onMilestoneChange={handleMilestoneChange}
      />
      <ManageLabels
        isOpen={isManageLabelsOpen}
        onClose={() => setIsManageLabelsOpen(false)}
        onLabelChange={handleLabelChange}
      />
      <ManageSort
        isOpen={isManageSortOpen}
        onClose={() => setIsManageSortOpen(false)}
        sortOrder={sortOrder}
        onSortChange={setSortOrder}
      />
    </Page>
  );
};

export default App;
