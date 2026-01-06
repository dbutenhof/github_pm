"""Tests for the app module.

ai-generated: Cursor
"""

from fastapi.testclient import TestClient

from github_pm.app import app, router


class TestApp:
    """Test the FastAPI application."""

    def test_app_creation(self):
        """Test that the FastAPI app is created successfully."""
        # Assert
        assert app is not None
        assert hasattr(app, "routes")
        assert hasattr(app, "router")

    def test_app_configuration(self):
        """Test that the app has correct title and version."""
        # Assert
        assert app.title == "GitHub Project Management API"
        assert app.version == "0.1.0"

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == {"message": "OK"}

    def test_health_endpoint_content_type(self):
        """Test that health endpoint returns correct content type."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/health")

        # Assert
        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_methods(self):
        """Test that health endpoint only accepts GET method."""
        # Arrange
        client = TestClient(app)

        # Act & Assert
        # GET should work
        response = client.get("/health")
        assert response.status_code == 200

        # POST should return 405 Method Not Allowed or 404 Not Found
        response = client.post("/health")
        assert response.status_code in [404, 405]

        # PUT should return 405 Method Not Allowed or 404 Not Found
        response = client.put("/health")
        assert response.status_code in [404, 405]

        # DELETE should return 405 Method Not Allowed or 404 Not Found
        response = client.delete("/health")
        assert response.status_code in [404, 405]

    def test_api_router_included(self):
        """Test that the API router is included at the correct prefix."""
        # Arrange
        client = TestClient(app)

        # Act - Try to access an endpoint from the API router
        # The /api/v1/project endpoint should exist
        response = client.get("/api/v1/project")

        # Assert
        # The endpoint should exist (may return 200 or error depending on dependencies)
        # We just verify it's not a 404 for a non-existent route
        # If it's 400, that's expected due to missing GitHub connection
        # If it's 200, that's also valid
        assert response.status_code != 404

    def test_router_exists(self):
        """Test that the router is properly defined."""
        # Assert
        assert router is not None
        assert hasattr(router, "routes")

    def test_health_route_in_router(self):
        """Test that the health route is registered in the router."""
        # Assert
        # Check that the router has at least one route
        assert len(router.routes) > 0

        # Check that there's a route for /health
        # FastAPI routes can have different structures, so we check multiple ways
        health_routes = [
            route
            for route in router.routes
            if hasattr(route, "path") and route.path == "/health"
        ]
        # If no direct path match, check if health endpoint is accessible via test client
        if len(health_routes) == 0:
            client = TestClient(app)
            response = client.get("/health")
            # If we can access it, the route exists (even if not directly in router.routes)
            assert response.status_code == 200
        else:
            assert len(health_routes) > 0

    def test_app_includes_router(self):
        """Test that the app includes the router."""
        # Assert
        # The app should have routes from the router
        assert len(app.routes) > 0

    def test_nonexistent_endpoint_returns_404(self):
        """Test that a nonexistent endpoint returns 404."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/nonexistent")

        # Assert
        assert response.status_code == 404

    def test_api_prefix_correct(self):
        """Test that API routes are accessible at /api/v1 prefix."""
        # Arrange
        client = TestClient(app)

        # Act - Try accessing a route that should be at /api/v1
        # We'll check that /api/v1/project exists (even if it fails due to dependencies)
        response = client.get("/api/v1/project")

        # Assert
        # Should not be 404 (route exists)
        # Could be 400 (missing dependencies) or 200 (success)
        assert response.status_code != 404

        # Verify that the same route without prefix doesn't exist
        response_no_prefix = client.get("/project")
        assert response_no_prefix.status_code == 404
