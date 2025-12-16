// Shared labels cache - loaded once and shared across all components
let labelsCache = {
  data: [],
  loading: false,
  error: null,
  promise: null,
};

export const getLabelsCache = () => labelsCache;

export const clearLabelsCache = () => {
  labelsCache.data = [];
  labelsCache.loading = false;
  labelsCache.error = null;
  labelsCache.promise = null;
};

export default labelsCache;
