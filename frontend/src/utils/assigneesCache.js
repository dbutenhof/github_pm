// ai-generated: Cursor
// Shared assignees cache - loaded once and shared across all components
let assigneesCache = {
  data: [],
  loading: false,
  error: null,
  promise: null,
};

export const getAssigneesCache = () => assigneesCache;

export const clearAssigneesCache = () => {
  assigneesCache.data = [];
  assigneesCache.loading = false;
  assigneesCache.error = null;
  assigneesCache.promise = null;
};

export default assigneesCache;
