# Assisted-by: Codex
"""Tests for the api module.

Generated-by: Cursor
"""

from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
import requests

from github_pm.api import (
    add_milestone_to_issue,
    api_router,
    close_issue_with_comment,
    CloseIssueRequest,
    connection,
    Connector,
    create_comment,
    create_issue,
    create_label,
    create_milestone,
    CreateComment,
    CreateIssue,
    CreateLabel,
    CreateMilestone,
    delete_label,
    delete_milestone,
    get_comment_reactions,
    get_comments,
    get_issue_reactions,
    get_labels,
    get_milestones,
    get_project,
    remove_milestone_from_issue,
    render_markdown,
    RenderMarkdown,
    update_comment,
    update_issue_body,
    update_issue_title,
    update_issue_type,
    update_label,
    UpdateComment,
    UpdateIssueBody,
    UpdateIssueTitle,
    UpdateIssueType,
    UpdateLabel,
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
            patch(
                "github_pm.github_client.requests.session", return_value=mock_session
            ),
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
                "github_pm.github_client.requests.session",
                side_effect=Exception("Auth failed"),
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
            patch(
                "github_pm.github_client.requests.session", return_value=mock_session
            ),
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
            patch(
                "github_pm.github_client.requests.session", return_value=mock_session
            ),
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
            mock_session.close.assert_called_once()


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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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

    @pytest.mark.asyncio
    async def test_get_milestones_sorts_versions_numerically_before_other_milestones(
        self,
    ):
        mock_milestones = [
            {"title": "v0.9.0", "number": 9},
            {"title": "Backlog", "number": 1},
            {"title": "v0.10.0", "number": 10},
            {"title": "v0.8.1", "number": 8},
        ]
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.get_paged = Mock(return_value=mock_milestones)

        result = await get_milestones(mock_gitctx)

        assert [milestone["title"] for milestone in result] == [
            "v0.8.1",
            "v0.9.0",
            "v0.10.0",
            "Backlog",
            "none",
        ]

    @pytest.mark.asyncio
    async def test_get_closed_milestones_omits_none_placeholder(self):
        mock_milestones = [{"title": "Completed", "number": 3}]
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.get_paged = Mock(return_value=mock_milestones)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await get_milestones(mock_gitctx, state="closed")

        assert result == mock_milestones
        mock_gitctx.get_paged.assert_called_once_with(
            "/repos/test/repo/milestones?state=closed",
            headers={"Accept": "application/vnd.github.full+json"},
        )


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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
                "/repos/test/repo/issues/123", data={"milestone": None}
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.delete = Mock(side_effect=Exception("Label not found"))

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            # Act & Assert
            with pytest.raises(Exception):
                await delete_label(mock_gitctx, label_name="nonexistent")


class TestUpdateLabel:
    """Test the update_label endpoint."""

    @pytest.mark.asyncio
    async def test_update_label_success(self):
        """Test successfully updating a label, including its name."""
        mock_label_response = {
            "id": 1,
            "name": "updated-label",
            "color": "green",
            "description": "Updated label",
        }
        label_data = UpdateLabel(
            name="updated-label", color="green", description="Updated label"
        )
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.patch = Mock(return_value=mock_label_response)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"

            result = await update_label(mock_gitctx, "old-label", label_data)

        assert result == mock_label_response
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/labels/old-label",
            data={
                "new_name": "updated-label",
                "color": "green",
                "description": "Updated label",
            },
        )


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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
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


class TestConnector504Retry:
    """Tests for ``Connector`` retry behavior on GitHub HTTP 504 responses."""

    def test_get_retries_504_then_succeeds(self):
        """504 then 200 triggers one backoff sleep and succeeds."""
        mock_session = Mock()
        r504 = Mock()
        r504.headers = {}
        r504.status_code = 504
        r200 = Mock()
        r200.headers = {}
        r200.status_code = 200
        r200.raise_for_status = Mock()
        r200.json.return_value = {"ok": True}
        mock_session.get.side_effect = [r504, r200]

        with (
            patch(
                "github_pm.github_client.requests.session", return_value=mock_session
            ),
            patch("github_pm.github_client.time.sleep") as mock_sleep,
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "o/r"
            mock_context.github_token = "tok"
            conn = Connector("tok", github_repo="o/r")
            data = conn.get("/repos/o/r/issues/1")

        assert data == {"ok": True}
        assert mock_session.get.call_count == 2
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == pytest.approx(1.5)

    def test_get_exhausts_retries_on_persistent_504(self):
        """After max attempts, persistent 504 propagates ``HTTPError``."""
        mock_session = Mock()
        r504 = Mock()
        r504.headers = {}
        r504.status_code = 504
        err = requests.HTTPError()
        err.response = r504
        r504.raise_for_status = Mock(side_effect=err)
        mock_session.get.return_value = r504

        with (
            patch(
                "github_pm.github_client.requests.session", return_value=mock_session
            ),
            patch("github_pm.github_client.time.sleep"),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "o/r"
            mock_context.github_token = "tok"
            conn = Connector("tok", github_repo="o/r")
            with pytest.raises(requests.HTTPError):
                conn.get("/repos/o/r/issues/1")

        assert mock_session.get.call_count == 5


class TestCreateComment:
    """Test the create_comment endpoint.

    Generated-by: Cursor
    """

    @pytest.mark.asyncio
    async def test_create_comment_success(self):
        mock_comment = {
            "id": 99,
            "body": "Hello",
            "body_html": "<p>Hello</p>",
        }
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_comment)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await create_comment(mock_gitctx, 42, CreateComment(body="Hello"))

        assert result == mock_comment
        mock_gitctx.post.assert_called_once_with(
            "/repos/test/repo/issues/42/comments",
            data={"body": "Hello"},
            headers={"Accept": "application/vnd.github.full+json"},
        )


class TestUpdateComment:
    """Test the update_comment endpoint.

    Generated-by: Cursor
    """

    @pytest.mark.asyncio
    async def test_update_comment_success(self):
        mock_comment = {
            "id": 99,
            "body": "Updated",
            "body_html": "<p>Updated</p>",
        }
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.patch = Mock(return_value=mock_comment)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await update_comment(
                mock_gitctx, 99, UpdateComment(body="Updated")
            )

        assert result == mock_comment
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/comments/99",
            data={"body": "Updated"},
            headers={"Accept": "application/vnd.github.full+json"},
        )


class TestUpdateIssueBody:
    """Test the update_issue_body endpoint.

    Generated-by: Cursor
    """

    @pytest.mark.asyncio
    async def test_update_issue_body_success(self):
        mock_issue = {
            "number": 42,
            "body": "New description",
            "body_html": "<p>New description</p>",
        }
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.patch = Mock(return_value=mock_issue)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await update_issue_body(
                mock_gitctx, 42, UpdateIssueBody(body="New description")
            )

        assert result == mock_issue
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/42",
            data={"body": "New description"},
            headers={"Accept": "application/vnd.github.full+json"},
        )

    @pytest.mark.asyncio
    async def test_update_issue_body_allows_empty(self):
        mock_issue = {"number": 42, "body": "", "body_html": ""}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.patch = Mock(return_value=mock_issue)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await update_issue_body(mock_gitctx, 42, UpdateIssueBody(body=""))

        assert result == mock_issue
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/42",
            data={"body": ""},
            headers={"Accept": "application/vnd.github.full+json"},
        )


class TestUpdateIssueTitle:
    """Test the update_issue_title endpoint.

    Assisted-by: openai-code-assist
    """

    @pytest.mark.asyncio
    async def test_update_issue_title_success(self):
        mock_issue = {
            "number": 42,
            "title": "Updated title",
        }
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.patch = Mock(return_value=mock_issue)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await update_issue_title(
                mock_gitctx, 42, UpdateIssueTitle(title="Updated title")
            )

        assert result == mock_issue
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/42",
            data={"title": "Updated title"},
            headers={"Accept": "application/vnd.github.full+json"},
        )


class TestUpdateIssueType:
    """Test the update_issue_type endpoint.

    Assisted-by: openai-code-assist
    """

    @pytest.mark.asyncio
    async def test_update_issue_type_success(self):
        mock_issue = {
            "number": 42,
            "type": {"name": "Task", "color": "green"},
        }
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.patch = Mock(return_value=mock_issue)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await update_issue_type(
                mock_gitctx, 42, UpdateIssueType(type="Task")
            )

        assert result == mock_issue
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/42",
            data={"type": "Task"},
            headers={"Accept": "application/vnd.github.full+json"},
        )


class TestCloseIssueWithComment:
    """Test the close_issue_with_comment endpoint.

    Generated-by: Cursor
    """

    @pytest.mark.asyncio
    async def test_close_with_comment_success(self):
        mock_comment = {"id": 1, "body": "Done"}
        mock_issue = {"number": 42, "state": "closed"}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_comment)
        mock_gitctx.patch = Mock(return_value=mock_issue)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await close_issue_with_comment(
                mock_gitctx, 42, CloseIssueRequest(reason="done", body="Done")
            )

        assert result == {"comment": mock_comment, "issue": mock_issue}
        mock_gitctx.post.assert_called_once_with(
            "/repos/test/repo/issues/42/comments",
            data={"body": "Done"},
            headers={"Accept": "application/vnd.github.full+json"},
        )
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/42",
            data={"state": "closed", "state_reason": "completed"},
            headers={"Accept": "application/vnd.github.full+json"},
        )

    @pytest.mark.asyncio
    async def test_close_with_obsolete_default_comment(self):
        mock_comment = {"id": 1, "body": "Obsolete"}
        mock_issue = {"number": 42, "state": "closed"}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_comment)
        mock_gitctx.patch = Mock(return_value=mock_issue)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await close_issue_with_comment(
                mock_gitctx,
                42,
                CloseIssueRequest(reason="obsolete", body="   "),
            )

        assert result == {"comment": mock_comment, "issue": mock_issue}
        mock_gitctx.post.assert_called_once_with(
            "/repos/test/repo/issues/42/comments",
            data={"body": "Obsolete"},
            headers={"Accept": "application/vnd.github.full+json"},
        )
        mock_gitctx.patch.assert_called_once_with(
            "/repos/test/repo/issues/42",
            data={"state": "closed", "state_reason": "not_planned"},
            headers={"Accept": "application/vnd.github.full+json"},
        )


class TestRenderMarkdown:
    """Test the render_markdown endpoint.

    Generated-by: Cursor
    """

    @pytest.mark.asyncio
    async def test_render_markdown_success(self):
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post_text = Mock(return_value="<p><strong>hi</strong></p>")

        result = await render_markdown(mock_gitctx, RenderMarkdown(text="**hi**"))

        assert result == {"html": "<p><strong>hi</strong></p>"}
        mock_gitctx.post_text.assert_called_once_with("/markdown/raw", "**hi**")

    @pytest.mark.asyncio
    async def test_render_markdown_empty(self):
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post_text = Mock(return_value="")

        result = await render_markdown(mock_gitctx, RenderMarkdown(text=""))

        assert result == {"html": ""}
        mock_gitctx.post_text.assert_called_once_with("/markdown/raw", "")


class TestCreateIssue:
    """Test the create_issue endpoint.

    Generated-by: Cursor
    """

    @pytest.mark.asyncio
    async def test_create_issue_basic(self):
        mock_created = {"id": 100, "number": 50, "title": "New"}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_created)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await create_issue(
                mock_gitctx,
                CreateIssue(title="New", body="Body text", type="Bug"),
            )

        assert result == mock_created
        call_args = mock_gitctx.post.call_args
        assert call_args[0][0] == "/repos/test/repo/issues"
        assert call_args[1]["data"]["title"] == "New"
        assert call_args[1]["data"]["body"] == "Body text"
        assert call_args[1]["data"]["type"] == "Bug"
        assert mock_gitctx.post.call_count == 1

    @pytest.mark.asyncio
    async def test_create_issue_with_milestone_labels_assignees(self):
        mock_created = {"id": 100, "number": 50, "title": "Epic"}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_created)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await create_issue(
                mock_gitctx,
                CreateIssue(
                    title="Epic",
                    labels=["enhancement"],
                    assignees=["alice"],
                    milestone=6,
                    type="Feature",
                ),
            )

        assert result["number"] == 50
        data = mock_gitctx.post.call_args[1]["data"]
        assert data["labels"] == ["enhancement"]
        assert data["assignees"] == ["alice"]
        assert data["milestone"] == 6
        assert data["type"] == "Feature"

    @pytest.mark.asyncio
    async def test_create_issue_skips_milestone_zero(self):
        mock_created = {"id": 100, "number": 50, "title": "No MS"}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_created)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            await create_issue(mock_gitctx, CreateIssue(title="No MS", milestone=0))

        assert "milestone" not in mock_gitctx.post.call_args[1]["data"]

    @pytest.mark.asyncio
    async def test_create_issue_with_parent(self):
        mock_created = {"id": 100, "number": 50, "title": "Child"}
        mock_gitctx = Mock(spec=Connector)
        mock_gitctx.owner, mock_gitctx.repo = "test", "repo"
        mock_gitctx.post = Mock(return_value=mock_created)

        with patch("github_pm.api.context") as mock_context:
            mock_context.github_repo = "test/repo"
            result = await create_issue(
                mock_gitctx,
                CreateIssue(title="Child", parent_number=10, milestone=6),
            )

        assert result["parent_number"] == 10
        assert mock_gitctx.post.call_count == 2
        parent_call = mock_gitctx.post.call_args_list[1]
        assert parent_call[0][0] == "/repos/test/repo/issues/10/sub_issues"
        assert parent_call[1]["data"] == {
            "sub_issue_id": 100,
            "replace_parent": True,
        }


class TestConnectorPostText:
    """Test Connector.post_text for markdown/raw.

    Generated-by: Cursor
    """

    def test_post_text_returns_response_text(self):
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_response.text = "<p>ok</p>"
        mock_session.post.return_value = mock_response

        with (
            patch(
                "github_pm.github_client.requests.session", return_value=mock_session
            ),
            patch("github_pm.api.context") as mock_context,
        ):
            mock_context.github_repo = "o/r"
            mock_context.github_token = "tok"
            conn = Connector("tok", github_repo="o/r")
            html = conn.post_text("/markdown/raw", "**ok**")

        assert html == "<p>ok</p>"
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args
        assert call_kwargs[0][0] == "https://api.github.com/markdown/raw"
        assert call_kwargs[1]["data"] == b"**ok**"
        assert call_kwargs[1]["headers"]["Content-Type"] == "text/plain; charset=utf-8"
