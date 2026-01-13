"""OAuth authentication module for GitHub.

ai-generated: Cursor
"""

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from github_pm.context import context

auth_router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def generate_state_token() -> str:
    """Generate a secure random state token for OAuth."""
    return secrets.token_urlsafe(32)


@auth_router.get("/login")
async def login(request: Request):
    """Initiate GitHub OAuth flow."""
    if not context.github_client_id:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth not configured. Please set GITHUB_CLIENT_ID.",
        )

    state = generate_state_token()
    request.session["oauth_state"] = state

    params = {
        "client_id": context.github_client_id,
        "redirect_uri": context.github_oauth_callback_url,
        "scope": "repo",
        "state": state,
    }
    auth_url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@auth_router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None):
    """Handle GitHub OAuth callback."""
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # Verify state
    session_state = request.session.get("oauth_state")
    if not session_state or state != session_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Clear state from session
    request.session.pop("oauth_state", None)

    # Exchange code for token
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": context.github_client_id,
                    "client_secret": context.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            if "error" in token_data:
                raise HTTPException(
                    status_code=400, detail=f"OAuth error: {token_data['error']}"
                )

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=400, detail="No access token in response"
                )

            # Get user info
            user_response = await client.get(
                GITHUB_USER_URL,
                headers={"Authorization": f"token {access_token}"},
            )
            user_response.raise_for_status()
            user_data = user_response.json()

            # Store in session
            request.session["github_token"] = access_token
            request.session["github_user"] = user_data.get("login")
            request.session["github_user_id"] = user_data.get("id")
            request.session["github_user_name"] = user_data.get("name")
            request.session["github_user_avatar"] = user_data.get("avatar_url")

            # Redirect to frontend
            return RedirectResponse(url="/")

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub API error: {e.response.status_code} - {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@auth_router.get("/logout")
async def logout(request: Request):
    """Clear session and log out user."""
    request.session.clear()
    return {"message": "Logged out successfully"}


@auth_router.get("/user")
async def get_user(request: Request):
    """Get current authenticated user info."""
    if "github_user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "username": request.session.get("github_user"),
        "user_id": request.session.get("github_user_id"),
        "name": request.session.get("github_user_name"),
        "avatar_url": request.session.get("github_user_avatar"),
        "authenticated": True,
    }


@auth_router.get("/status")
async def auth_status(request: Request):
    """Check authentication status."""
    is_authenticated = "github_user" in request.session
    return {
        "authenticated": is_authenticated,
        "username": request.session.get("github_user") if is_authenticated else None,
    }
