// Generated-by: Codex
import { createMetadataCache, invalidateQueries } from './queryCache';
const milestonesCache = createMetadataCache();
export const getMilestonesCache = () => milestonesCache;
export const clearMilestonesCache = () => {
  milestonesCache.clear();
  invalidateQueries('/milestones');
};
export default milestonesCache;
