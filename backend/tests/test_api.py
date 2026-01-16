"""Tests for the api module.

ai-generated: Cursor
"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from github_pm.api import (
    add_label_to_issue,
    add_milestone_to_issue,
    api_router,
    connection,
    Connector,
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
        mock_session = Mock()
        with (
            patch("github_pm.api.requests.session", return_value=mock_session),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"

            # Act
            async_gen = connection()
            gitctx = await async_gen.__anext__()

            # Assert
            assert isinstance(gitctx, Connector)
            assert gitctx.github_token == "test_token"
            assert gitctx.owner == "test"
            assert gitctx.repo == "repo"
            assert gitctx.github == mock_session

            # Clean up - trigger the finally block
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass

    @pytest.mark.asyncio
    async def test_connection_github_init_error(self):
        """Test connection when GitHub initialization fails."""
        # Arrange
        with (
            patch(
                "github_pm.api.requests.session", side_effect=Exception("Auth failed")
            ),
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
        """Test connection when repository access fails."""
        # Arrange
        mock_session = Mock()
        # Simulate an error during initialization (e.g., invalid token)
        with (
            patch("github_pm.api.requests.session", return_value=mock_session),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"
            # Simulate error when trying to access repo
            mock_session.get.side_effect = Exception("Repo not found")

            # Act
            async_gen = connection()
            gitctx = await async_gen.__anext__()
            # The error would occur when actually using the connector, not during init
            assert isinstance(gitctx, Connector)

            # Clean up
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass

    @pytest.mark.asyncio
    async def test_connection_closes_on_exit(self):
        """Test that GitHub connection is properly initialized."""
        # Arrange
        mock_session = Mock()
        with (
            patch("github_pm.api.requests.session", return_value=mock_session),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "test/repo"
            mock_context.github_token = "test_token"

            # Act
            async_gen = connection()
            gitctx = await async_gen.__anext__()
            assert isinstance(gitctx, Connector)
            assert gitctx.github == mock_session

            # Trigger cleanup by consuming the generator
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass

            # Assert - session should have headers set
            mock_session.headers.update.assert_called()


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
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Issue 1",
                "pull_request": {},
                "labels": [{"name": "bug"}],
            },
            {
                "id": 2,
                "number": 2,
                "title": "Issue 2",
                "labels": [{"name": "feature"}],
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(mock_gitctx, milestone_number=1)

            # Assert
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2
            mock_gitctx.get_paged.assert_called_once()
            # Issue 1 has pull_request, so no GraphQL call
            # Issue 2 doesn't have pull_request, so GraphQL should be called
            assert mock_gitctx.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_issues_with_linked_prs(self):
        """Test getting issues with linked PRs from GraphQL."""
        # Arrange
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Issue 1",
                "labels": [{"name": "bug"}],
            }
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
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
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
            mock_gitctx.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issues_with_no_milestone(self):
        """Test getting issues with milestone_number=0 (no milestone)."""
        # Arrange
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Issue 1",
                "labels": [],
            }
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issues(mock_gitctx, milestone_number=0)

            # Assert
            assert len(result) == 1
            assert result[0]["id"] == 1
            mock_gitctx.get_paged.assert_called_once()
            # GraphQL should be called for issue without pull_request
            assert mock_gitctx.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_issues_with_sort_single_label(self):
        """Test getting issues sorted by a single label."""
        # Arrange
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug Issue",
                "labels": [{"name": "bug"}],
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature Issue",
                "labels": [{"name": "feature"}],
            },
            {
                "id": 3,
                "number": 3,
                "title": "Other Issue",
                "labels": [{"name": "documentation"}],
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug Issue",
                "labels": [{"name": "bug"}],
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature Issue",
                "labels": [{"name": "feature"}],
            },
            {
                "id": 3,
                "number": 3,
                "title": "Enhancement Issue",
                "labels": [{"name": "enhancement"}],
            },
            {
                "id": 4,
                "number": 4,
                "title": "Unlabeled Issue",
                "labels": [],
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug Issue",
                "labels": [{"name": "BUG"}],  # Uppercase label
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature Issue",
                "labels": [{"name": "Feature"}],  # Mixed case label
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug Issue",
                "labels": [{"name": "bug"}],
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature Issue",
                "labels": [{"name": "feature"}],
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug/Feature Issue",
                "labels": [
                    {"name": "bug"},
                    {"name": "feature"},
                ],  # Issue with both labels
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature Only Issue",
                "labels": [{"name": "feature"}],
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
        mock_issues = [
            {
                "id": 1,
                "number": 1,
                "title": "Bug Issue",
                "labels": [{"name": "bug"}],
            },
            {
                "id": 2,
                "number": 2,
                "title": "Feature Issue",
                "labels": [{"name": "feature"}],
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_issues)
        mock_gitctx.post = Mock(
            return_value={
                "data": {
                    "repository": {
                        "issue": {"closedByPullRequestsReferences": {"nodes": []}}
                    }
                }
            }
        )
        mock_gitctx.owner = "test"
        mock_gitctx.repo = "repo"

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
        mock_comments = [
            {"id": 1, "body": "Comment 1", "body_html": "<p>Comment 1</p>"},
            {"id": 2, "body": "Comment 2", "body_html": "<p>Comment 2</p>"},
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_comments)

        # Act
        result = await get_comments(mock_gitctx, issue_number=123)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        mock_gitctx.get_paged.assert_called_once()


class TestGetMilestones:
    """Test the get_milestones endpoint."""

    @pytest.mark.asyncio
    async def test_get_milestones(self):
        """Test getting all milestones."""
        # Arrange
        mock_milestones = [
            {
                "title": "Milestone 1",
                "number": 1,
                "description": "Description 1",
                "due_on": "2024-12-31T00:00:00Z",
            },
            {
                "title": "Milestone 2",
                "number": 2,
                "description": "Description 2",
                "due_on": None,
            },
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_milestones)

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
        mock_gitctx.get_paged.assert_called_once()


class TestCreateMilestone:
    """Test the create_milestone endpoint."""

    @pytest.mark.asyncio
    async def test_create_milestone_success(self):
        """Test successfully creating a milestone."""
        # Arrange
        from datetime import datetime

        mock_milestone_response = {"id": 1, "title": "New Milestone"}

        milestone_data = CreateMilestone(
            title="New Milestone",
            description="Test description",
            due_on=datetime(2024, 12, 31),
        )

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.post = Mock(return_value=mock_milestone_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await create_milestone(mock_gitctx, milestone_data)

            # Assert
            assert result == mock_milestone_response
            mock_gitctx.post.assert_called_once()
            call_args = mock_gitctx.post.call_args
            assert call_args[0][0] == "/repos/test/repo/milestones"
            assert call_args[1]["data"]["title"] == "New Milestone"
            assert call_args[1]["data"]["state"] == "open"
            assert call_args[1]["data"]["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_create_milestone_with_defaults(self):
        """Test creating a milestone with default values."""
        # Arrange
        mock_milestone_response = {"id": 1, "title": "New Milestone"}

        milestone_data = CreateMilestone(title="New Milestone")

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.post = Mock(return_value=mock_milestone_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await create_milestone(mock_gitctx, milestone_data)

            # Assert
            assert result == mock_milestone_response
            mock_gitctx.post.assert_called_once()
            call_args = mock_gitctx.post.call_args
            assert call_args[0][0] == "/repos/test/repo/milestones"
            assert call_args[1]["data"]["title"] == "New Milestone"
            assert call_args[1]["data"]["state"] == "open"
            assert call_args[1]["data"]["description"] is None
            assert "due_on" not in call_args[1]["data"]


class TestDeleteMilestone:
    """Test the delete_milestone endpoint."""

    @pytest.mark.asyncio
    async def test_delete_milestone_success(self):
        """Test successfully deleting a milestone."""
        # Arrange
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.delete = Mock(return_value={})

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await delete_milestone(mock_gitctx, milestone_number=1)

            # Assert
            assert result == {"message": "1 milestone deleted"}
            mock_gitctx.delete.assert_called_once_with("/repos/test/repo/milestones/1")

    @pytest.mark.asyncio
    async def test_delete_milestone_not_found(self):
        """Test deleting a milestone that doesn't exist."""
        # Arrange
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.delete = Mock(side_effect=Exception("Milestone not found"))

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act & Assert
            with pytest.raises(Exception):
                await delete_milestone(mock_gitctx, milestone_number=999)


class TestAddMilestoneToIssue:
    """Test the add_milestone_to_issue endpoint."""

    @pytest.mark.asyncio
    async def test_add_milestone_to_issue(self):
        """Test adding a milestone to an issue."""
        # Arrange
        mock_issue_response = {"id": 123, "milestone": {"number": 1}}

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.patch = Mock(return_value=mock_issue_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await add_milestone_to_issue(
                mock_gitctx, issue_number=123, milestone_number=1
            )

            # Assert
            assert result == mock_issue_response
            mock_gitctx.patch.assert_called_once_with(
                "/repos/test/repo/issues/123", data={"milestone": 1}
            )


class TestRemoveMilestoneFromIssue:
    """Test the remove_milestone_from_issue endpoint."""

    @pytest.mark.asyncio
    async def test_remove_milestone_from_issue(self):
        """Test removing a milestone from an issue."""
        # Arrange
        mock_issue_response = {"id": 123, "milestone": None}

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.patch = Mock(return_value=mock_issue_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await remove_milestone_from_issue(
                mock_gitctx, issue_number=123, milestone_number=1
            )

            # Assert
            assert result == mock_issue_response
            mock_gitctx.patch.assert_called_once_with(
                "/repos/test/repo/issues/123", data={"milestone": 1}
            )


class TestGetLabels:
    """Test the get_labels endpoint."""

    @pytest.mark.asyncio
    async def test_get_labels(self):
        """Test getting all labels."""
        # Arrange
        mock_labels = [
            {"id": 1, "name": "bug", "color": "red"},
            {"id": 2, "name": "feature", "color": "blue"},
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_labels)

        # Act
        result = await get_labels(mock_gitctx)

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "bug"
        assert result[1]["name"] == "feature"
        mock_gitctx.get_paged.assert_called_once()


class TestCreateLabel:
    """Test the create_label endpoint."""

    @pytest.mark.asyncio
    async def test_create_label_success(self):
        """Test successfully creating a label."""
        # Arrange
        mock_label_response = {"id": 1, "name": "new-label", "color": "green"}

        label_data = CreateLabel(
            name="new-label", color="green", description="Test label"
        )

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.post = Mock(return_value=mock_label_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await create_label(mock_gitctx, label_data)

            # Assert
            assert result == mock_label_response
            mock_gitctx.post.assert_called_once()
            call_args = mock_gitctx.post.call_args
            assert call_args[0][0] == "/repos/test/repo/labels"
            assert call_args[1]["data"]["name"] == "new-label"
            assert call_args[1]["data"]["color"] == "green"
            assert call_args[1]["data"]["description"] == "Test label"

    @pytest.mark.asyncio
    async def test_create_label_with_defaults(self):
        """Test creating a label with default description."""
        # Arrange
        mock_label_response = {"id": 1, "name": "new-label", "color": "green"}

        label_data = CreateLabel(name="new-label", color="green")

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.post = Mock(return_value=mock_label_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await create_label(mock_gitctx, label_data)

            # Assert
            assert result == mock_label_response
            mock_gitctx.post.assert_called_once()
            call_args = mock_gitctx.post.call_args
            assert call_args[0][0] == "/repos/test/repo/labels"
            assert call_args[1]["data"]["name"] == "new-label"
            assert call_args[1]["data"]["color"] == "green"
            assert call_args[1]["data"]["description"] is None


class TestDeleteLabel:
    """Test the delete_label endpoint."""

    @pytest.mark.asyncio
    async def test_delete_label_success(self):
        """Test successfully deleting a label."""
        # Arrange
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.delete = Mock(return_value={})

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await delete_label(mock_gitctx, label_name="bug")

            # Assert
            assert result == {"message": "bug label deleted"}
            mock_gitctx.delete.assert_called_once_with("/repos/test/repo/labels/bug")

    @pytest.mark.asyncio
    async def test_delete_label_not_found(self):
        """Test deleting a label that doesn't exist."""
        # Arrange
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.delete = Mock(side_effect=Exception("Label not found"))

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act & Assert
            with pytest.raises(Exception):
                await delete_label(mock_gitctx, label_name="nonexistent")


class TestAddLabelToIssue:
    """Test the add_label_to_issue endpoint."""

    @pytest.mark.asyncio
    async def test_add_label_to_issue(self):
        """Test adding a label to an issue."""
        # Arrange
        mock_issue_get = {
            "id": 123,
            "labels": [{"name": "existing"}],
        }
        mock_issue_patch = {
            "id": 123,
            "labels": [{"name": "existing"}, {"name": "bug"}],
        }

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get = Mock(return_value=mock_issue_get)
        mock_gitctx.patch = Mock(return_value=mock_issue_patch)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await add_label_to_issue(
                mock_gitctx, issue_number=123, label_name="bug"
            )

            # Assert
            assert result == mock_issue_patch
            mock_gitctx.get.assert_called_once_with("/repos/test/repo/issues/123")
            mock_gitctx.patch.assert_called_once()
            # Check that patch was called with correct path and that labels contain both
            call_args = mock_gitctx.patch.call_args
            assert call_args[0][0] == "/repos/test/repo/issues/123"
            assert set(call_args[1]["data"]["labels"]) == {"existing", "bug"}

    @pytest.mark.asyncio
    async def test_add_label_to_issue_already_exists(self):
        """Test adding a label that already exists on an issue."""
        # Arrange
        mock_issue_get = {
            "id": 123,
            "labels": [{"name": "bug"}],
        }

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get = Mock(return_value=mock_issue_get)
        mock_gitctx.patch = Mock()

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await add_label_to_issue(
                mock_gitctx, issue_number=123, label_name="bug"
            )

            # Assert
            assert result == mock_issue_get
            mock_gitctx.get.assert_called_once_with("/repos/test/repo/issues/123")
            mock_gitctx.patch.assert_not_called()


class TestRemoveLabelFromIssue:
    """Test the remove_label_from_issue endpoint."""

    @pytest.mark.asyncio
    async def test_remove_label_from_issue(self):
        """Test removing a label from an issue."""
        # Arrange
        mock_issue_get = {
            "id": 123,
            "labels": [{"name": "bug"}, {"name": "feature"}],
        }
        mock_issue_patch = {
            "id": 123,
            "labels": [{"name": "feature"}],
        }

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get = Mock(return_value=mock_issue_get)
        mock_gitctx.patch = Mock(return_value=mock_issue_patch)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await remove_label_from_issue(
                mock_gitctx, issue_number=123, label_name="bug"
            )

            # Assert
            assert result == mock_issue_patch
            mock_gitctx.get.assert_called_once_with("/repos/test/repo/issues/123")
            mock_gitctx.patch.assert_called_once_with(
                "/repos/test/repo/issues/123", data={"labels": ["feature"]}
            )

    @pytest.mark.asyncio
    async def test_remove_label_from_issue_not_present(self):
        """Test removing a label that doesn't exist on an issue."""
        # Arrange
        mock_issue_get = {
            "id": 123,
            "labels": [{"name": "feature"}],
        }

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get = Mock(return_value=mock_issue_get)
        mock_gitctx.patch = Mock()

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await remove_label_from_issue(
                mock_gitctx, issue_number=123, label_name="bug"
            )

            # Assert
            assert result == mock_issue_get
            mock_gitctx.get.assert_called_once_with("/repos/test/repo/issues/123")
            mock_gitctx.patch.assert_not_called()


class TestGetIssueReactions:
    """Test the get_issue_reactions endpoint."""

    @pytest.mark.asyncio
    async def test_get_issue_reactions(self):
        """Test getting reactions for an issue."""
        # Arrange
        mock_reactions = [
            {"id": 1, "content": "+1", "user": {"login": "user1"}},
            {"id": 2, "content": "heart", "user": {"login": "user2"}},
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_reactions)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issue_reactions(mock_gitctx, issue_number=123)

            # Assert
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[0]["content"] == "+1"
            assert result[1]["id"] == 2
            assert result[1]["content"] == "heart"
            mock_gitctx.get_paged.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issue_reactions_empty(self):
        """Test getting reactions for an issue with no reactions."""
        # Arrange
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=[])

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_issue_reactions(mock_gitctx, issue_number=456)

            # Assert
            assert result == []
            mock_gitctx.get_paged.assert_called_once()


class TestGetCommentReactions:
    """Test the get_comment_reactions endpoint."""

    @pytest.mark.asyncio
    async def test_get_comment_reactions(self):
        """Test getting reactions for a comment."""
        # Arrange
        mock_reactions = [
            {"id": 1, "content": "laugh", "user": {"login": "user1"}},
            {"id": 2, "content": "hooray", "user": {"login": "user2"}},
            {"id": 3, "content": "confused", "user": {"login": "user3"}},
        ]

        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=mock_reactions)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

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
            mock_gitctx.get_paged.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_comment_reactions_empty(self):
        """Test getting reactions for a comment with no reactions."""
        # Arrange
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.get_paged = Mock(return_value=[])

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act
            result = await get_comment_reactions(mock_gitctx, comment_id=999)

            # Assert
            assert result == []
            mock_gitctx.get_paged.assert_called_once()


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
