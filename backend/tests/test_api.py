"""Tests for the api module.

ai-generated: Cursor
"""

from datetime import date
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from github_pm.api import (
    add_label_to_issue,
    add_milestone_to_issue,
    api_router,
    connection,
    create_label,
    create_milestone,
    CreateLabel,
    CreateMilestone,
    delete_label,
    delete_milestone,
    get_comment_reactions,
    get_comments,
    get_issue_reactions,
    get_issues,
    get_labels,
    get_milestones,
    get_project,
    GitHubCtx,
    remove_label_from_issue,
    remove_milestone_from_issue,
)
from github_pm.app import app


class TestConnection:
    """Test the connection dependency."""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful GitHub connection."""
        # Arrange
        mock_repo = Mock()
        mock_repo.name = "test-repo"
        mock_github = Mock()
        mock_github.get_repo.return_value = mock_repo

        with (
            patch("github_pm.api.Github", return_value=mock_github),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"

            # Act
            async_gen = connection()
            gitctx = await async_gen.__anext__()

            # Assert
            assert isinstance(gitctx, GitHubCtx)
            assert gitctx.repo == mock_repo
            assert gitctx.github == mock_github
            mock_github.get_repo.assert_called_once_with("test/repo")

            # Clean up - trigger the finally block
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass
            mock_github.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_github_init_error(self):
        """Test connection when GitHub initialization fails."""
        # Arrange
        with (
            patch("github_pm.api.Github", side_effect=Exception("Auth failed")),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"

            # Act & Assert
            async_gen = connection()
            with pytest.raises(HTTPException) as exc_info:
                await async_gen.__anext__()
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_connection_get_repo_error(self):
        """Test connection when get_repo fails."""
        # Arrange
        mock_github = Mock()
        mock_github.get_repo.side_effect = Exception("Repo not found")

        with (
            patch("github_pm.api.Github", return_value=mock_github),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"

            # Act & Assert
            async_gen = connection()
            with pytest.raises(HTTPException) as exc_info:
                await async_gen.__anext__()
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_connection_closes_on_exit(self):
        """Test that GitHub connection is closed after use."""
        # Arrange
        mock_repo = Mock()
        mock_repo.name = "test-repo"
        mock_github = Mock()
        mock_github.get_repo.return_value = mock_repo

        with (
            patch("github_pm.api.Github", return_value=mock_github),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"

            # Act
            async_gen = connection()
            gitctx = await async_gen.__anext__()
            assert isinstance(gitctx, GitHubCtx)
            assert gitctx.repo == mock_repo

            # Trigger cleanup by consuming the generator
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass

            # Assert
            mock_github.close.assert_called_once()


class TestGetProject:
    """Test the get_project endpoint."""

    @pytest.mark.asyncio
    async def test_get_project(self):
        """Test getting project information."""
        # Arrange
        with patch("github_pm.api.context") as mock_context:
            mock_context.app_name = "Test App"
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_project()

            # Assert
            assert result == {
                "app_name": "Test App",
                "github_repo": "test/repo",
            }


class TestGetIssues:
    """Test the get_issues endpoint."""

    @pytest.mark.asyncio
    async def test_get_issues_with_milestone(self):
        """Test getting issues for a specific milestone."""
        # Arrange
        mock_milestone = Mock()
        mock_milestone.title = "Test Milestone"
        mock_label1 = Mock()
        mock_label1.name = "bug"
        mock_label2 = Mock()
        mock_label2.name = "feature"
        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Issue 1", "pull_request": {}}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label1]
        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Issue 2"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label2]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1, mock_issue2])

        mock_repo = Mock()
        mock_repo.get_milestone.return_value = mock_milestone
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(mock_gitctx, milestone_number=1)

            # Assert
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2
            mock_repo.get_milestone.assert_called_once_with(1)
            mock_repo.get_issues.assert_called_once_with(
                milestone=mock_milestone, state="open"
            )
            # Issue 1 has pull_request, so no GraphQL call
            # Issue 2 doesn't have pull_request, so GraphQL should be called
            assert mock_requester.graphql_query.call_count == 1

    @pytest.mark.asyncio
    async def test_get_issues_with_linked_prs(self):
        """Test getting issues with linked PRs from GraphQL."""
        # Arrange
        mock_milestone = Mock()
        mock_milestone.title = "Test Milestone"
        mock_label = Mock()
        mock_label.name = "bug"
        mock_issue = Mock()
        mock_issue.raw_data = {"id": 1, "title": "Issue 1"}
        mock_issue.number = 1
        mock_issue.labels = [mock_label]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue])

        mock_repo = Mock()
        mock_repo.get_milestone.return_value = mock_milestone
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {
                            "closedByPullRequestsReferences": {
                                "nodes": [
                                    {
                                        "number": 123,
                                        "title": "Fix Issue 1",
                                        "url": "https://github.com/test/repo/pull/123",
                                    },
                                    {
                                        "number": 456,
                                        "title": "Another fix",
                                        "url": "https://github.com/test/repo/pull/456",
                                    },
                                ]
                            }
                        }
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(mock_gitctx, milestone_number=1)

            # Assert
            assert len(result) == 1
            assert result[0]["id"] == 1
            assert "closed_by" in result[0]
            assert len(result[0]["closed_by"]) == 2
            assert result[0]["closed_by"][0]["number"] == 123
            assert result[0]["closed_by"][0]["title"] == "Fix Issue 1"
            assert (
                result[0]["closed_by"][0]["url"]
                == "https://github.com/test/repo/pull/123"
            )
            assert result[0]["closed_by"][1]["number"] == 456
            mock_requester.graphql_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issues_with_no_milestone(self):
        """Test getting issues with milestone_number=0 (no milestone)."""
        # Arrange
        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Issue 1"}
        mock_issue1.number = 1
        mock_issue1.labels = []

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1])

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(mock_gitctx, milestone_number=0)

            # Assert
            assert len(result) == 1
            assert result[0]["id"] == 1
            mock_repo.get_issues.assert_called_once_with(milestone="none", state="open")
            mock_repo.get_milestone.assert_not_called()
            # GraphQL should be called for issue without pull_request
            assert mock_requester.graphql_query.call_count == 1

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_single_label(self):
        """Test getting issues sorted by a single label."""
        # Arrange
        mock_label_bug = Mock()
        mock_label_bug.name = "bug"
        mock_label_feature = Mock()
        mock_label_feature.name = "feature"
        mock_label_other = Mock()
        mock_label_other.name = "documentation"

        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Bug Issue"}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label_bug]

        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Feature Issue"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label_feature]

        mock_issue3 = Mock()
        mock_issue3.raw_data = {"id": 3, "title": "Other Issue"}
        mock_issue3.number = 3
        mock_issue3.labels = [mock_label_other]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1, mock_issue2, mock_issue3])

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(mock_gitctx, milestone_number=0, sort="bug")

            # Assert
            assert len(result) == 3
            # First should be bug issue
            assert result[0]["id"] == 1
            assert result[0]["title"] == "Bug Issue"
            # Then other issues
            assert result[1]["id"] == 2
            assert result[2]["id"] == 3

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_multiple_labels(self):
        """Test getting issues sorted by multiple labels in order."""
        # Arrange
        mock_label_bug = Mock()
        mock_label_bug.name = "bug"
        mock_label_feature = Mock()
        mock_label_feature.name = "feature"
        mock_label_enhancement = Mock()
        mock_label_enhancement.name = "enhancement"

        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Bug Issue"}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label_bug]

        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Feature Issue"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label_feature]

        mock_issue3 = Mock()
        mock_issue3.raw_data = {"id": 3, "title": "Enhancement Issue"}
        mock_issue3.number = 3
        mock_issue3.labels = [mock_label_enhancement]

        mock_issue4 = Mock()
        mock_issue4.raw_data = {"id": 4, "title": "Unlabeled Issue"}
        mock_issue4.number = 4
        mock_issue4.labels = []

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues(
            [mock_issue1, mock_issue2, mock_issue3, mock_issue4]
        )

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(
                mock_gitctx, milestone_number=0, sort="bug,feature,enhancement"
            )

            # Assert
            assert len(result) == 4
            # Order should be: bug, feature, enhancement, other
            assert result[0]["id"] == 1  # bug
            assert result[1]["id"] == 2  # feature
            assert result[2]["id"] == 3  # enhancement
            assert result[3]["id"] == 4  # other (unlabeled)

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_case_insensitive(self):
        """Test that label matching is case-insensitive."""
        # Arrange
        mock_label_bug = Mock()
        mock_label_bug.name = "BUG"  # Uppercase label
        mock_label_feature = Mock()
        mock_label_feature.name = "Feature"  # Mixed case label

        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Bug Issue"}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label_bug]

        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Feature Issue"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label_feature]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1, mock_issue2])

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act - using lowercase sort labels
            result = await get_issues(
                mock_gitctx, milestone_number=0, sort="bug,feature"
            )

            # Assert
            assert len(result) == 2
            # Should match despite case difference
            assert result[0]["id"] == 1  # bug (matched "BUG")
            assert result[1]["id"] == 2  # feature (matched "Feature")

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_whitespace_stripped(self):
        """Test that whitespace in sort parameter is stripped."""
        # Arrange
        mock_label_bug = Mock()
        mock_label_bug.name = "bug"
        mock_label_feature = Mock()
        mock_label_feature.name = "feature"

        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Bug Issue"}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label_bug]

        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Feature Issue"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label_feature]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1, mock_issue2])

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act - with whitespace in sort parameter
            result = await get_issues(
                mock_gitctx, milestone_number=0, sort=" bug , feature "
            )

            # Assert
            assert len(result) == 2
            # Should match despite whitespace
            assert result[0]["id"] == 1  # bug
            assert result[1]["id"] == 2  # feature

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_first_match_wins(self):
        """Test that issues matching multiple labels go to the first matching label."""
        # Arrange
        mock_label_bug = Mock()
        mock_label_bug.name = "bug"
        mock_label_feature = Mock()
        mock_label_feature.name = "feature"

        # Issue with both labels
        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Bug/Feature Issue"}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label_bug, mock_label_feature]

        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Feature Only Issue"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label_feature]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1, mock_issue2])

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act - bug comes first in sort order
            result = await get_issues(
                mock_gitctx, milestone_number=0, sort="bug,feature"
            )

            # Assert
            assert len(result) == 2
            # Issue 1 should be in bug category (first match), not feature
            assert result[0]["id"] == 1  # bug (first match wins)
            assert result[1]["id"] == 2  # feature

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_all_other(self):
        """Test that issues without sort parameter all go to 'other'."""
        # Arrange
        mock_label_bug = Mock()
        mock_label_bug.name = "bug"
        mock_label_feature = Mock()
        mock_label_feature.name = "feature"

        mock_issue1 = Mock()
        mock_issue1.raw_data = {"id": 1, "title": "Bug Issue"}
        mock_issue1.number = 1
        mock_issue1.labels = [mock_label_bug]

        mock_issue2 = Mock()
        mock_issue2.raw_data = {"id": 2, "title": "Feature Issue"}
        mock_issue2.number = 2
        mock_issue2.labels = [mock_label_feature]

        # Create an iterable mock with totalCount
        class IterableIssues:
            def __init__(self, issues):
                self.issues = issues
                self.totalCount = len(issues)

            def __iter__(self):
                return iter(self.issues)

        mock_issues_obj = IterableIssues([mock_issue1, mock_issue2])

        mock_repo = Mock()
        mock_repo.get_issues.return_value = mock_issues_obj

        mock_requester = Mock()
        mock_requester.graphql_query.return_value = (
            None,
            {
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            },
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act - no sort parameter
            result = await get_issues(mock_gitctx, milestone_number=0, sort=None)

            # Assert
            assert len(result) == 2
            # Both should be in "other" since no sort labels specified
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2


class TestGetComments:
    """Test the get_comments endpoint."""

    @pytest.mark.asyncio
    async def test_get_comments(self):
        """Test getting comments for an issue."""
        # Arrange
        mock_comment1 = Mock()
        mock_comment1.raw_data = {"id": 1, "body": "Comment 1"}
        mock_comment2 = Mock()
        mock_comment2.raw_data = {"id": 2, "body": "Comment 2"}
        mock_comments = Mock()
        mock_comments.__iter__ = Mock(return_value=iter([mock_comment1, mock_comment2]))

        mock_issue = Mock()
        mock_issue.get_comments.return_value = mock_comments

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_comments(mock_gitctx, issue_number=123)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.get_comments.assert_called_once()


class TestGetMilestones:
    """Test the get_milestones endpoint."""

    @pytest.mark.asyncio
    async def test_get_milestones(self):
        """Test getting all milestones."""
        # Arrange
        mock_milestone1 = Mock()
        mock_milestone1.title = "Milestone 1"
        mock_milestone1.number = 1
        mock_milestone1.description = "Description 1"
        mock_milestone1.due_on = date(2024, 12, 31)

        mock_milestone2 = Mock()
        mock_milestone2.title = "Milestone 2"
        mock_milestone2.number = 2
        mock_milestone2.description = "Description 2"
        mock_milestone2.due_on = None

        mock_milestones = Mock()
        mock_milestones.__iter__ = Mock(
            return_value=iter([mock_milestone1, mock_milestone2])
        )

        mock_repo = Mock()
        mock_repo.get_milestones.return_value = mock_milestones

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_milestones(mock_gitctx)

        # Assert
        assert len(result) == 3  # 2 milestones + 1 "none" milestone
        assert result[0]["title"] == "Milestone 1"
        assert result[0]["number"] == 1
        assert result[1]["title"] == "Milestone 2"
        assert result[1]["number"] == 2
        assert result[2]["title"] == "none"
        assert result[2]["number"] == 0
        assert result[2]["due_on"] is None


class TestCreateMilestone:
    """Test the create_milestone endpoint."""

    @pytest.mark.asyncio
    async def test_create_milestone_success(self):
        """Test successfully creating a milestone."""
        # Arrange
        mock_milestone = Mock()
        mock_milestone.raw_data = {"id": 1, "title": "New Milestone"}

        mock_repo = Mock()
        mock_repo.create_milestone.return_value = mock_milestone

        milestone_data = CreateMilestone(
            title="New Milestone",
            description="Test description",
            due_on=date(2024, 12, 31),
        )

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await create_milestone(mock_gitctx, milestone_data)

        # Assert
        assert result == mock_milestone.raw_data
        mock_repo.create_milestone.assert_called_once_with(
            title="New Milestone",
            state="open",
            description="Test description",
            due_on=date(2024, 12, 31),
        )

    @pytest.mark.asyncio
    async def test_create_milestone_with_defaults(self):
        """Test creating a milestone with default values."""
        # Arrange
        from github.GithubObject import NotSet

        mock_milestone = Mock()
        mock_milestone.raw_data = {"id": 1, "title": "New Milestone"}

        mock_repo = Mock()
        mock_repo.create_milestone.return_value = mock_milestone

        milestone_data = CreateMilestone(title="New Milestone")

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await create_milestone(mock_gitctx, milestone_data)

        # Assert
        assert result == mock_milestone.raw_data
        mock_repo.create_milestone.assert_called_once_with(
            title="New Milestone", state="open", description=NotSet, due_on=NotSet
        )


class TestDeleteMilestone:
    """Test the delete_milestone endpoint."""

    @pytest.mark.asyncio
    async def test_delete_milestone_success(self):
        """Test successfully deleting a milestone."""
        # Arrange
        mock_milestone = Mock()
        mock_milestone.delete = Mock()

        mock_repo = Mock()
        mock_repo.get_milestone.return_value = mock_milestone

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await delete_milestone(mock_gitctx, milestone_number=1)

        # Assert
        assert result == {"message": "1 milestone deleted"}
        mock_repo.get_milestone.assert_called_once_with(1)
        mock_milestone.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_milestone_not_found(self):
        """Test deleting a milestone that doesn't exist."""
        # Arrange
        mock_repo = Mock()
        mock_repo.get_milestone.side_effect = Exception("Milestone not found")

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act & Assert
        with pytest.raises(Exception):
            await delete_milestone(mock_gitctx, milestone_number=999)


class TestAddMilestoneToIssue:
    """Test the add_milestone_to_issue endpoint."""

    @pytest.mark.asyncio
    async def test_add_milestone_to_issue(self):
        """Test adding a milestone to an issue."""
        # Arrange
        mock_issue = Mock()
        mock_issue.edit = Mock()

        mock_milestone = Mock()

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue
        mock_repo.get_milestone.return_value = mock_milestone

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await add_milestone_to_issue(
            mock_gitctx, issue_number=123, milestone_number=1
        )

        # Assert
        assert result == {"message": "1 milestone added to issue 123"}
        mock_repo.get_issue.assert_called_once_with(123)
        mock_repo.get_milestone.assert_called_once_with(1)
        mock_issue.edit.assert_called_once_with(milestone=mock_milestone)


class TestRemoveMilestoneFromIssue:
    """Test the remove_milestone_from_issue endpoint."""

    @pytest.mark.asyncio
    async def test_remove_milestone_from_issue(self):
        """Test removing a milestone from an issue."""
        # Arrange
        mock_issue = Mock()
        mock_issue.edit = Mock()

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await remove_milestone_from_issue(
            mock_gitctx, issue_number=123, milestone_number=1
        )

        # Assert
        assert result == {"message": "1 milestone removed from issue 123"}
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.edit.assert_called_once_with(milestone=None)


class TestGetLabels:
    """Test the get_labels endpoint."""

    @pytest.mark.asyncio
    async def test_get_labels(self):
        """Test getting all labels."""
        # Arrange
        mock_label1 = Mock()
        mock_label1.raw_data = {"id": 1, "name": "bug", "color": "red"}
        mock_label2 = Mock()
        mock_label2.raw_data = {"id": 2, "name": "feature", "color": "blue"}

        mock_labels = Mock()
        mock_labels.__iter__ = Mock(return_value=iter([mock_label1, mock_label2]))

        mock_repo = Mock()
        mock_repo.get_labels.return_value = mock_labels

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_labels(mock_gitctx)

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "bug"
        assert result[1]["name"] == "feature"
        mock_repo.get_labels.assert_called_once()


class TestCreateLabel:
    """Test the create_label endpoint."""

    @pytest.mark.asyncio
    async def test_create_label_success(self):
        """Test successfully creating a label."""
        # Arrange
        mock_label = Mock()
        mock_label.name = "new-label"
        mock_label.raw_data = {"id": 1, "name": "new-label", "color": "green"}

        mock_repo = Mock()
        mock_repo.create_label.return_value = mock_label

        label_data = CreateLabel(
            name="new-label", color="green", description="Test label"
        )

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await create_label(mock_gitctx, label_data)

        # Assert
        assert result == mock_label.raw_data
        mock_repo.create_label.assert_called_once_with(
            name="new-label", color="green", description="Test label"
        )

    @pytest.mark.asyncio
    async def test_create_label_with_defaults(self):
        """Test creating a label with default description."""
        # Arrange
        from github.GithubObject import NotSet

        mock_label = Mock()
        mock_label.name = "new-label"
        mock_label.raw_data = {"id": 1, "name": "new-label", "color": "green"}

        mock_repo = Mock()
        mock_repo.create_label.return_value = mock_label

        label_data = CreateLabel(name="new-label", color="green")

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await create_label(mock_gitctx, label_data)

        # Assert
        assert result == mock_label.raw_data
        mock_repo.create_label.assert_called_once_with(
            name="new-label", color="green", description=NotSet
        )


class TestDeleteLabel:
    """Test the delete_label endpoint."""

    @pytest.mark.asyncio
    async def test_delete_label_success(self):
        """Test successfully deleting a label."""
        # Arrange
        mock_label = Mock()
        mock_label.delete = Mock()

        mock_repo = Mock()
        mock_repo.get_label.return_value = mock_label

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await delete_label(mock_gitctx, label_name="bug")

        # Assert
        assert result == {"message": "bug label deleted"}
        mock_repo.get_label.assert_called_once_with("bug")
        mock_label.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_label_not_found(self):
        """Test deleting a label that doesn't exist."""
        # Arrange
        mock_repo = Mock()
        mock_repo.get_label.side_effect = Exception("Label not found")

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act & Assert
        with pytest.raises(Exception):
            await delete_label(mock_gitctx, label_name="nonexistent")


class TestAddLabelToIssue:
    """Test the add_label_to_issue endpoint."""

    @pytest.mark.asyncio
    async def test_add_label_to_issue(self):
        """Test adding a label to an issue."""
        # Arrange
        mock_issue = Mock()
        mock_issue.add_to_labels = Mock()

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await add_label_to_issue(
            mock_gitctx, issue_number=123, label_name="bug"
        )

        # Assert
        assert result == {"message": "bug label added to issue 123"}
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.add_to_labels.assert_called_once_with("bug")


class TestRemoveLabelFromIssue:
    """Test the remove_label_from_issue endpoint."""

    @pytest.mark.asyncio
    async def test_remove_label_from_issue(self):
        """Test removing a label from an issue."""
        # Arrange
        mock_issue = Mock()
        mock_issue.remove_from_labels = Mock()

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_github = Mock()
        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await remove_label_from_issue(
            mock_gitctx, issue_number=123, label_name="bug"
        )

        # Assert
        assert result is None
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.remove_from_labels.assert_called_once_with("bug")


class TestGetIssueReactions:
    """Test the get_issue_reactions endpoint."""

    @pytest.mark.asyncio
    async def test_get_issue_reactions(self):
        """Test getting reactions for an issue."""
        # Arrange
        mock_repo = Mock()
        mock_repo.url = "https://api.github.com/repos/test/repo"

        mock_requester = Mock()
        mock_requester.requestJsonAndCheck.return_value = (
            {"Content-Type": "application/json"},
            [
                {"id": 1, "content": "+1", "user": {"login": "user1"}},
                {"id": 2, "content": "heart", "user": {"login": "user2"}},
            ],
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_issue_reactions(mock_gitctx, issue_number=123)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["content"] == "+1"
        assert result[1]["id"] == 2
        assert result[1]["content"] == "heart"
        mock_requester.requestJsonAndCheck.assert_called_once_with(
            "GET", "https://api.github.com/repos/test/repo/issues/123/reactions"
        )

    @pytest.mark.asyncio
    async def test_get_issue_reactions_empty(self):
        """Test getting reactions for an issue with no reactions."""
        # Arrange
        mock_repo = Mock()
        mock_repo.url = "https://api.github.com/repos/test/repo"

        mock_requester = Mock()
        mock_requester.requestJsonAndCheck.return_value = (
            {"Content-Type": "application/json"},
            [],
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_issue_reactions(mock_gitctx, issue_number=456)

        # Assert
        assert result == []
        mock_requester.requestJsonAndCheck.assert_called_once_with(
            "GET", "https://api.github.com/repos/test/repo/issues/456/reactions"
        )


class TestGetCommentReactions:
    """Test the get_comment_reactions endpoint."""

    @pytest.mark.asyncio
    async def test_get_comment_reactions(self):
        """Test getting reactions for a comment."""
        # Arrange
        mock_repo = Mock()
        mock_repo.url = "https://api.github.com/repos/test/repo"

        mock_requester = Mock()
        mock_requester.requestJsonAndCheck.return_value = (
            {"Content-Type": "application/json"},
            [
                {"id": 1, "content": "laugh", "user": {"login": "user1"}},
                {"id": 2, "content": "hooray", "user": {"login": "user2"}},
                {"id": 3, "content": "confused", "user": {"login": "user3"}},
            ],
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_comment_reactions(mock_gitctx, comment_id=789)

        # Assert
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[0]["content"] == "laugh"
        assert result[1]["id"] == 2
        assert result[1]["content"] == "hooray"
        assert result[2]["id"] == 3
        assert result[2]["content"] == "confused"
        mock_requester.requestJsonAndCheck.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/test/repo/issues/comments/789/reactions",
        )

    @pytest.mark.asyncio
    async def test_get_comment_reactions_empty(self):
        """Test getting reactions for a comment with no reactions."""
        # Arrange
        mock_repo = Mock()
        mock_repo.url = "https://api.github.com/repos/test/repo"

        mock_requester = Mock()
        mock_requester.requestJsonAndCheck.return_value = (
            {"Content-Type": "application/json"},
            [],
        )

        mock_github = Mock()
        mock_github.requester = mock_requester

        mock_gitctx = GitHubCtx(github=mock_github, repo=mock_repo)

        # Act
        result = await get_comment_reactions(mock_gitctx, comment_id=999)

        # Assert
        assert result == []
        mock_requester.requestJsonAndCheck.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/test/repo/issues/comments/999/reactions",
        )


class TestAPIRouterIntegration:
    """Test API router integration with FastAPI app."""

    def test_api_router_exists(self):
        """Test that api_router is defined."""
        # Assert
        assert api_router is not None
        assert hasattr(api_router, "routes")

    def test_api_endpoints_registered(self):
        """Test that API endpoints are registered in the router."""
        # Assert
        assert len(api_router.routes) > 0

    def test_get_project_endpoint(self):
        """Test the /api/v1/project endpoint via TestClient."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/api/v1/project")

        # Assert
        # Should succeed (doesn't require GitHub connection)
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "github_repo" in data
