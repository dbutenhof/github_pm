// Assisted-by: Codex
// Generated-by: Cursor
import {
  cachedQuery,
  invalidateQueries,
  setQueryRepository,
} from '../utils/queryCache';
const API_BASE = '/api/v1';

// Generated-by: Codex
const apiFetch = async (url, options) => {
  const mutation =
    options?.method && options.method !== 'GET' && !url.endsWith('/markdown');
  if (mutation) invalidateQueries();
  try {
    return await (options ? fetch(url, options) : fetch(url));
  } finally {
    // A timeout can follow an accepted write, so invalidate on failure too.
    if (mutation) invalidateQueries();
  }
};

const readJson = async (path, message) => {
  const response = await apiFetch(`${API_BASE}${path}`);
  await raiseForResponse(response, message);
  return response.json();
};

const readErrorDetail = async (response) => {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string' && body.detail.trim()) {
      return body.detail;
    }
    if (body?.detail != null) {
      return JSON.stringify(body.detail);
    }
    if (typeof body?.message === 'string' && body.message.trim()) {
      return body.message;
    }
  } catch {
    // Ignore non-JSON error bodies.
  }
  return response.statusText || `HTTP ${response.status}`;
};

const raiseForResponse = async (response, fallback) => {
  if (response.ok) {
    return;
  }
  const detail = await readErrorDetail(response);
  throw new Error(`${fallback}: ${detail}`);
};

export const fetchMilestones = (state = 'open', options = {}) => {
  const path = `/milestones${state === 'open' ? '' : `?state=${encodeURIComponent(state)}`}`;
  return cachedQuery(
    path,
    () => readJson(path, 'Failed to fetch milestones'),
    options
  );
};

// Assisted-by: openai-code-assist
export const fetchMilestoneOpenCounts = async (milestoneNumber) => {
  const response = await apiFetch(
    `${API_BASE}/milestones/${milestoneNumber}/open-counts`
  );
  if (!response.ok) {
    throw new Error(
      `Failed to fetch milestone open counts: ${response.statusText}`
    );
  }
  return response.json();
};

export const fetchIssues = (milestoneNumber, _sortOrder = [], options = {}) => {
  const path = `/issues/${milestoneNumber}`;
  return cachedQuery(path, () => readJson(path, 'Failed to fetch issues'), {
    ttl: 15000,
    ...options,
  });
};

// Generated-by: Cline
export const fetchIssueFields = (options = {}) => {
  const path = '/issue-fields';
  return cachedQuery(
    path,
    () => readJson(path, 'Failed to fetch issue fields'),
    { ttl: 60000, ...options }
  );
};

export const fetchComments = (issueNumber) =>
  cachedQuery(
    `/comments/${issueNumber}`,
    () => readJson(`/comments/${issueNumber}`, 'Failed to fetch comments'),
    { ttl: 15000 }
  );

export const createComment = async (issueNumber, body) => {
  const response = await apiFetch(`${API_BASE}/comments/${issueNumber}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ body }),
  });
  if (!response.ok) {
    throw new Error(`Failed to create comment: ${response.statusText}`);
  }
  return response.json();
};

export const updateComment = async (commentId, body) => {
  const response = await apiFetch(`${API_BASE}/comments/${commentId}/body`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ body }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update comment: ${response.statusText}`);
  }
  return response.json();
};

export const updateIssueBody = async (issueNumber, body) => {
  const response = await apiFetch(`${API_BASE}/issues/${issueNumber}/body`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ body }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update issue body: ${response.statusText}`);
  }
  return response.json();
};

export const updateIssueTitle = async (issueNumber, title) => {
  const response = await apiFetch(`${API_BASE}/issues/${issueNumber}/title`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update issue title: ${response.statusText}`);
  }
  return response.json();
};

// Assisted-by: openai-code-assist
export const updateIssueType = async (issueNumber, type) => {
  const response = await apiFetch(`${API_BASE}/issues/${issueNumber}/type`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update issue type: ${response.statusText}`);
  }
  return response.json();
};

// Generated-by: Cline
export const setIssueFieldValue = async (issueNumber, fieldId, optionId) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/fields/${encodeURIComponent(fieldId)}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ option_id: optionId ?? null }),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update issue field: ${response.statusText}`);
  }
  return response.json();
};

export const closeIssue = async (issueNumber, { reason, body }) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/close-with-comment`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ reason, body }),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to close issue: ${response.statusText}`);
  }
  return response.json();
};

export const renderMarkdown = async (text) => {
  return cachedQuery(
    `markdown:${text}`,
    async () => {
      const response = await apiFetch(`${API_BASE}/markdown`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        throw new Error(`Failed to render markdown: ${response.statusText}`);
      }
      return response.json();
    },
    { ttl: 300000 }
  );
};
export const createIssue = async (issueData) => {
  const response = await apiFetch(`${API_BASE}/issues`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(issueData),
  });
  if (!response.ok) {
    throw new Error(`Failed to create issue: ${response.statusText}`);
  }
  return response.json();
};

export const fetchProject = async () => {
  const data = await readJson('/project', 'Failed to fetch project');
  setQueryRepository(data.github_repo);
  return data;
};

export const fetchLabels = (options = {}) =>
  cachedQuery(
    '/labels',
    () => readJson('/labels', 'Failed to fetch labels'),
    options
  );

export const addLabel = async (issueNumber, labelName) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/labels/${encodeURIComponent(labelName)}`,
    {
      method: 'POST',
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to add label: ${response.statusText}`);
  }
  return response.json();
};

export const removeLabel = async (issueNumber, labelName) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/labels/${encodeURIComponent(labelName)}`,
    {
      method: 'DELETE',
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to remove label: ${response.statusText}`);
  }
  return response.json();
};

export const createMilestone = async (milestoneData) => {
  const response = await apiFetch(`${API_BASE}/milestones`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(milestoneData),
  });
  if (!response.ok) {
    throw new Error(`Failed to create milestone: ${response.statusText}`);
  }
  return response.json();
};

// Assisted-by: openai-code-assist
export const updateMilestone = async (milestoneNumber, milestoneData) => {
  const response = await apiFetch(`${API_BASE}/milestones/${milestoneNumber}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(milestoneData),
  });
  if (!response.ok) {
    throw new Error(`Failed to update milestone: ${response.statusText}`);
  }
  return response.json();
};

// Assisted-by: openai-code-assist
export const updateMilestoneState = async (milestoneNumber, state) => {
  const response = await apiFetch(
    `${API_BASE}/milestones/${milestoneNumber}/state`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ state }),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update milestone state: ${response.statusText}`);
  }
  return response.json();
};

export const deleteMilestone = async (milestoneNumber) => {
  const response = await apiFetch(`${API_BASE}/milestones/${milestoneNumber}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete milestone: ${response.statusText}`);
  }
  return response.json();
};

export const createLabel = async (labelData) => {
  const response = await apiFetch(`${API_BASE}/labels`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(labelData),
  });
  if (!response.ok) {
    throw new Error(`Failed to create label: ${response.statusText}`);
  }
  return response.json();
};

// Assisted-by: openai-code-assist
export const updateLabel = async (labelName, labelData) => {
  const response = await apiFetch(
    `${API_BASE}/labels/${encodeURIComponent(labelName)}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(labelData),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update label: ${response.statusText}`);
  }
  return response.json();
};

export const deleteLabel = async (labelName) => {
  const response = await apiFetch(
    `${API_BASE}/labels/${encodeURIComponent(labelName)}`,
    {
      method: 'DELETE',
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to delete label: ${response.statusText}`);
  }
  return response.json();
};

export const setIssueMilestone = async (issueNumber, milestoneNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/milestone/${milestoneNumber}`,
    {
      method: 'POST',
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to set milestone: ${response.statusText}`);
  }
  return response.json();
};

export const removeIssueMilestone = async (issueNumber, milestoneNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/milestone/${milestoneNumber}`,
    {
      method: 'DELETE',
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to remove milestone: ${response.statusText}`);
  }
  return response.json();
};

export const setIssueParent = async (issueNumber, parentNumber) => {
  const response = await apiFetch(`${API_BASE}/issues/${issueNumber}/parent`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ parent_number: parentNumber }),
  });
  if (!response.ok) {
    throw new Error(`Failed to set parent: ${response.statusText}`);
  }
  return response.json();
};

export const clearIssueParent = async (issueNumber) => {
  const response = await apiFetch(`${API_BASE}/issues/${issueNumber}/parent`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to clear parent: ${response.statusText}`);
  }
  return response.json();
};

export const adoptParentMilestone = async (issueNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/adopt-parent-milestone`,
    {
      method: 'POST',
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to adopt parent milestone: ${response.statusText}`);
  }
  return response.json();
};

export const addBlockedBy = async (issueNumber, relatedIssueNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/dependencies/blocked_by`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ issue_number: relatedIssueNumber }),
    }
  );
  await raiseForResponse(response, 'Failed to add blocked-by link');
  return response.json();
};

export const removeBlockedBy = async (issueNumber, blockingIssueNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/dependencies/blocked_by/${blockingIssueNumber}`,
    {
      method: 'DELETE',
    }
  );
  await raiseForResponse(response, 'Failed to remove blocked-by link');
  return response.json();
};

export const addBlocking = async (issueNumber, relatedIssueNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/dependencies/blocking`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ issue_number: relatedIssueNumber }),
    }
  );
  await raiseForResponse(response, 'Failed to add blocking link');
  return response.json();
};

export const removeBlocking = async (issueNumber, blockedIssueNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/dependencies/blocking/${blockedIssueNumber}`,
    {
      method: 'DELETE',
    }
  );
  await raiseForResponse(response, 'Failed to remove blocking link');
  return response.json();
};

// Assisted-by: openai-code-assist
export const addClosedBy = async (issueNumber, pullRequestNumber) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/close-references`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ pull_request_number: pullRequestNumber }),
    }
  );
  await raiseForResponse(response, 'Failed to add closed-by link');
  return response.json();
};

export const fetchIssueReactions = (issueNumber) =>
  cachedQuery(
    `/issues/${issueNumber}/reactions`,
    () =>
      readJson(
        `/issues/${issueNumber}/reactions`,
        'Failed to fetch issuereactions'
      ),
    { ttl: 15000 }
  );

export const fetchCommentReactions = (commentId) =>
  cachedQuery(
    `/comments/${commentId}/reactions`,
    () =>
      readJson(
        `/comments/${commentId}/reactions`,
        'Failed to fetch commentreactions'
      ),
    { ttl: 15000 }
  );

export const fetchAssignees = (options = {}) =>
  cachedQuery(
    '/assignees',
    () => readJson('/assignees', 'Failed to fetch assignees'),
    options
  );

export const setIssueAssignees = async (issueNumber, assignees) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/assignees`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(assignees),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to set assignees: ${response.statusText}`);
  }
  return response.json();
};

export const removeIssueAssignees = async (issueNumber, assignees) => {
  const response = await apiFetch(
    `${API_BASE}/issues/${issueNumber}/assignees`,
    {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(assignees),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to remove assignees: ${response.statusText}`);
  }
  return response.json();
};

export const fetchSdlcDelivery = async (weeks = 4, weekDays = 7) => {
  const params = new URLSearchParams({
    weeks: String(weeks),
    week_days: String(weekDays),
  });
  const response = await apiFetch(`${API_BASE}/sdlc/delivery?${params}`);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch SDLC delivery metrics: ${response.statusText}`
    );
  }
  return response.json();
};

export const fetchEscapedDefectRate = async (weeks = 4, weekDays = 7) => {
  const params = new URLSearchParams({
    weeks: String(weeks),
    week_days: String(weekDays),
  });
  const response = await apiFetch(
    `${API_BASE}/sdlc/escaped-defect-rate?${params}`
  );
  if (!response.ok) {
    throw new Error(
      `Failed to fetch escaped defect rate: ${response.statusText}`
    );
  }
  return response.json();
};

export const fetchBugBacklogDelta = async (weeks = 4, weekDays = 7) => {
  const params = new URLSearchParams({
    weeks: String(weeks),
    week_days: String(weekDays),
  });
  const response = await apiFetch(
    `${API_BASE}/sdlc/bug-backlog-delta?${params}`
  );
  if (!response.ok) {
    throw new Error(
      `Failed to fetch bug backlog delta: ${response.statusText}`
    );
  }
  return response.json();
};

/**
 * @param {string} [startDateISO] ``YYYY-MM-DD`` — first calendar day of the window (UTC).
 * @param {string} [endDateISO] ``YYYY-MM-DD`` — last calendar day of the window (UTC).
 */
export const fetchProjectStatusReport = async (startDateISO, endDateISO) => {
  const params = new URLSearchParams();
  if (startDateISO) {
    params.set('start_date', startDateISO);
  }
  if (endDateISO) {
    params.set('end_date', endDateISO);
  }
  const qs = params.toString();
  const url = qs
    ? `${API_BASE}/project-status?${qs}`
    : `${API_BASE}/project-status`;
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch project status report: ${response.statusText}`
    );
  }
  return response.json();
};

// Generated-by: Codex
export const fetchSdlcDashboard = (weeks = 4, weekDays = 7, options = {}) => {
  const path = `/sdlc/dashboard?${new URLSearchParams({ weeks: String(weeks), week_days: String(weekDays) })}`;
  return cachedQuery(
    path,
    () => readJson(path, 'Failed to fetch SDLC metrics'),
    { ttl: 15000, ...options }
  );
};
