// ai-generated: Cursor
// Shared milestones cache - loaded once and shared across all components
let milestonesCache = {
  data: [],
  loading: false,
  error: null,
  promise: null,
};

export const getMilestonesCache = () => milestonesCache;

export const clearMilestonesCache = () => {
  milestonesCache.data = [];
  milestonesCache.loading = false;
  milestonesCache.error = null;
  milestonesCache.promise = null;
};

export default milestonesCache;
