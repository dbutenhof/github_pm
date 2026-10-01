// Generated-by: openai-code-assist

const VERSION_PATTERN = /^v(\d+)\.(\d+)\.(\d+)$/;

const versionParts = (title) => {
  const match = VERSION_PATTERN.exec(title || '');
  return match ? match.slice(1).map(Number) : null;
};

// Assisted-by: openai-code-assist
export const compareMilestones = (left, right) => {
  const leftIsNoMilestone = left.number === 0;
  const rightIsNoMilestone = right.number === 0;
  if (leftIsNoMilestone !== rightIsNoMilestone) {
    return leftIsNoMilestone ? 1 : -1;
  }

  const leftVersion = versionParts(left.title);
  const rightVersion = versionParts(right.title);
  if (leftVersion && rightVersion) {
    for (let index = 0; index < leftVersion.length; index += 1) {
      if (leftVersion[index] !== rightVersion[index]) {
        return leftVersion[index] - rightVersion[index];
      }
    }
    return 0;
  }
  if (leftVersion) return -1;
  if (rightVersion) return 1;

  return String(left.title || '').localeCompare(String(right.title || ''));
};

export const sortMilestones = (milestones) =>
  [...milestones].sort(compareMilestones);
