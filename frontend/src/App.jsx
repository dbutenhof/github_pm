// ai-generated: Cursor
import React, { useState, useEffect } from 'react';
import {
  Page,
  PageSection,
  Title,
  Spinner,
  Alert,
  Bullseye,
  Button,
} from '@patternfly/react-core';
import { fetchMilestones, fetchProject, fetchLabels } from './services/api';
import MilestoneCard from './components/MilestoneCard';
import ManageMilestones from './components/ManageMilestones';
import ManageLabels from './components/ManageLabels';
import ManageSort from './components/ManageSort';
import milestonesCache from './utils/milestonesCache';
import labelsCache, { clearLabelsCache } from './utils/labelsCache';

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
  const [sortOrder, setSortOrder] = useState([]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const handleLabelChange = () => {
    // Labels are cached in IssueCard, so we don't need to do anything here
    // but we can add a callback if needed in the future
  };

  return (
    <Page>
      <PageSection>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}
        >
          <Title headingLevel="h1" size="2xl">
            {projectLoading
              ? 'Loading...'
              : project
                ? `${project.app_name}: ${project.github_repo}`
                : 'GitHub Project Manager'}
          </Title>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
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
      </PageSection>
      <PageSection>
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

        {!loading && !error && milestones.length === 0 && (
          <Alert variant="info" title="No milestones found">
            There are no milestones available.
          </Alert>
        )}

        {!loading && !error && milestones.length > 0 && (
          <div
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
          >
            {milestones.map((milestone) => (
              <MilestoneCard
                key={milestone.number}
                milestone={milestone}
                sortOrder={sortOrder}
              />
            ))}
          </div>
        )}
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
