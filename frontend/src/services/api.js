// ai-generated: Cursor
const API_BASE = '/api/v1';

// Helper function to handle API requests with authentication
const apiRequest = async (url, options = {}) => {
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Important for cookies/sessions
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (response.status === 401) {
    // Unauthorized - redirect to login
    window.location.href = '/api/v1/auth/login';
    throw new Error('Unauthorized - redirecting to login');
  }

  if (!response.ok) {
    throw new Error(`Failed to fetch: ${response.statusText}`);
  }

  return response.json();
};

export const fetchMilestones = async () => {
  return apiRequest(`${API_BASE}/milestones`);
};

export const fetchIssues = async (milestoneNumber, sortOrder = []) => {
  let url = `${API_BASE}/issues/${milestoneNumber}`;
  if (sortOrder && sortOrder.length > 0) {
    const sortParam = sortOrder.join(',');
    url += `?sort=${encodeURIComponent(sortParam)}`;
  }
  return apiRequest(url);
};

export const fetchComments = async (issueNumber) => {
  return apiRequest(`${API_BASE}/comments/${issueNumber}`);
};

export const fetchProject = async () => {
  return apiRequest(`${API_BASE}/project`);
};

export const fetchLabels = async () => {
  return apiRequest(`${API_BASE}/labels`);
};

export const addLabel = async (issueNumber, labelName) => {
  return apiRequest(`${API_BASE}/issues/${issueNumber}/labels/${labelName}`, {
    method: 'POST',
  });
};

export const removeLabel = async (issueNumber, labelName) => {
  return apiRequest(`${API_BASE}/issues/${issueNumber}/labels/${labelName}`, {
    method: 'DELETE',
  });
};

export const createMilestone = async (milestoneData) => {
  return apiRequest(`${API_BASE}/milestones`, {
    method: 'POST',
    body: JSON.stringify(milestoneData),
  });
};

export const deleteMilestone = async (milestoneNumber) => {
  return apiRequest(`${API_BASE}/milestones/${milestoneNumber}`, {
    method: 'DELETE',
  });
};

export const createLabel = async (labelData) => {
  return apiRequest(`${API_BASE}/labels`, {
    method: 'POST',
    body: JSON.stringify(labelData),
  });
};

export const deleteLabel = async (labelName) => {
  return apiRequest(`${API_BASE}/labels/${labelName}`, {
    method: 'DELETE',
  });
};

export const setIssueMilestone = async (issueNumber, milestoneNumber) => {
  return apiRequest(
    `${API_BASE}/issues/${issueNumber}/milestone/${milestoneNumber}`,
    {
      method: 'POST',
    }
  );
};

export const removeIssueMilestone = async (issueNumber, milestoneNumber) => {
  return apiRequest(
    `${API_BASE}/issues/${issueNumber}/milestone/${milestoneNumber}`,
    {
      method: 'DELETE',
    }
  );
};
