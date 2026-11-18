// Generated-by: Codex
import { createMetadataCache, invalidateQueries } from './queryCache';
const assigneesCache = createMetadataCache();
export const getAssigneesCache = () => assigneesCache;
export const clearAssigneesCache = () => {
  assigneesCache.clear();
  invalidateQueries('/assignees');
};
export default assigneesCache;
