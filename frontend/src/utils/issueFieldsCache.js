// Generated-by: Cline
import { fetchIssueFields } from '../services/api';
import { createMetadataCache, invalidateQueries } from './queryCache';

const issueFieldsCache = createMetadataCache();

/**
 * Load the repository issue-field catalog once and share in-flight reads.
 */
export const loadIssueFields = () => {
  if (issueFieldsCache.loaded) {
    return Promise.resolve(issueFieldsCache.data);
  }
  if (issueFieldsCache.promise) {
    return issueFieldsCache.promise;
  }
  issueFieldsCache.loading = true;
  issueFieldsCache.error = null;
  issueFieldsCache.promise = Promise.resolve()
    .then(() => fetchIssueFields())
    .then((data) => {
      const fields = Array.isArray(data?.fields) ? data.fields : [];
      issueFieldsCache.data = fields;
      return fields;
    })
    .catch((error) => {
      issueFieldsCache.error = error?.message || String(error);
      return [];
    })
    .finally(() => {
      issueFieldsCache.loading = false;
      issueFieldsCache.promise = null;
    });
  return issueFieldsCache.promise;
};

export const clearIssueFieldsCache = () => {
  issueFieldsCache.clear();
  invalidateQueries('/issue-fields');
};

export default issueFieldsCache;
