"""OAuth authentication module for GitHub App acting on behalf of users.

ai-generated: Cursor
"""

import secrets
import time
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from github_pm.context import context

auth_router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def generate_state_token() -> str:
    """Generate a secure random state token for OAuth."""
    return secrets.token_urlsafe(32)


def generate_app_jwt() -> str:
    """Generate a JWT token for GitHub App authentication."""
    if not context.github_app_id or not context.github_app_private_key:
        raise HTTPException(
            status_code=500,
            detail="GitHub App not configured. Please set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY.",
        )

    # Parse the private key (handle both PEM string and file path)
    private_key = context.github_app_private_key
    if private_key.startswith("-----BEGIN"):
        # It's already a PEM string
        pass
    else:
        # Assume it's a file path or try to load it
        try:
            with open(private_key, "r") as f:
                private_key = f.read()
        except FileNotFoundError:
            # Assume it's already the key content
            pass

    # Generate JWT
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued at time (1 minute ago to account for clock skew)
        "exp": now + 600,  # Expires in 10 minutes
        "iss": context.github_app_id,  # Issuer (App ID)
    }

    try:
        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate app JWT: {str(e)}"
        )


@auth_router.get("/login")
async def login(request: Request):
    """Initiate GitHub OAuth flow for GitHub App."""
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
        "scope": "user",  # Request user access
        "state": state,
    }
    auth_url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@auth_router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None):
    """Handle GitHub OAuth callback and exchange for user-to-server token."""
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # Verify state
    session_state = request.session.get("oauth_state")
    if not session_state or state != session_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Clear state from session
    request.session.pop("oauth_state", None)

    try:
        # Exchange authorization code for access token
        # For GitHub Apps configured as OAuth apps, this returns a user-to-server token
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
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_response.raise_for_status()
            user_data = user_response.json()

        # Store in session (outside the client context)
        request.session["github_token"] = access_token
        request.session["github_user"] = user_data.get("login")
        request.session["github_user_id"] = user_data.get("id")
        request.session["github_user_name"] = user_data.get("name")
        request.session["github_user_avatar"] = user_data.get("avatar_url")

        # Redirect to frontend
        return RedirectResponse(url="http://localhost:3000")

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
