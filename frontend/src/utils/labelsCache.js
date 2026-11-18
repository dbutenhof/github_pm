// Generated-by: Codex
import { createMetadataCache, invalidateQueries } from './queryCache';
const labelsCache = createMetadataCache();
export const getLabelsCache = () => labelsCache;
export const clearLabelsCache = () => {
  labelsCache.clear();
  invalidateQueries('/labels');
};
export default labelsCache;
