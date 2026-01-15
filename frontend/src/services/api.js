// ai-generated: Cursor
const API_BASE = '/api/v1';

export const fetchMilestones = async () => {
  const response = await fetch(`${API_BASE}/milestones`);
  if (!response.ok) {
    throw new Error(`Failed to fetch milestones: ${response.statusText}`);
  }
  return response.json();
};

export const fetchIssues = async (milestoneNumber, sortOrder = []) => {
  let url = `${API_BASE}/issues/${milestoneNumber}`;
  if (sortOrder && sortOrder.length > 0) {
    const sortParam = sortOrder.join(',');
    url += `?sort=${encodeURIComponent(sortParam)}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch issues: ${response.statusText}`);
  }
  return response.json();
};

export const fetchComments = async (issueNumber) => {
  const response = await fetch(`${API_BASE}/comments/${issueNumber}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch comments: ${response.statusText}`);
  }
  return response.json();
};

export const fetchProject = async () => {
  const response = await fetch(`${API_BASE}/project`);
  if (!response.ok) {
    throw new Error(`Failed to fetch project: ${response.statusText}`);
  }
  return response.json();
};

export const fetchLabels = async () => {
  const response = await fetch(`${API_BASE}/labels`);
  if (!response.ok) {
    throw new Error(`Failed to fetch labels: ${response.statusText}`);
  }
  return response.json();
};

export const addLabel = async (issueNumber, labelName) => {
  const response = await fetch(
    `${API_BASE}/issues/${issueNumber}/labels/${labelName}`,
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
  const response = await fetch(
    `${API_BASE}/issues/${issueNumber}/labels/${labelName}`,
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
  const response = await fetch(`${API_BASE}/milestones`, {
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

export const deleteMilestone = async (milestoneNumber) => {
  const response = await fetch(`${API_BASE}/milestones/${milestoneNumber}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete milestone: ${response.statusText}`);
  }
  return response.json();
};

export const createLabel = async (labelData) => {
  const response = await fetch(`${API_BASE}/labels`, {
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

export const deleteLabel = async (labelName) => {
  const response = await fetch(`${API_BASE}/labels/${labelName}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete label: ${response.statusText}`);
  }
  return response.json();
};

export const setIssueMilestone = async (issueNumber, milestoneNumber) => {
  const response = await fetch(
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
  const response = await fetch(
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

export const fetchIssueReactions = async (issueNumber) => {
  const response = await fetch(`${API_BASE}/issues/${issueNumber}/reactions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch issue reactions: ${response.statusText}`);
  }
  return response.json();
};

export const fetchCommentReactions = async (commentId) => {
  const response = await fetch(`${API_BASE}/comments/${commentId}/reactions`);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch comment reactions: ${response.statusText}`
    );
  }
  return response.json();
};
