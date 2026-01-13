from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from github_pm.api import api_router
from github_pm.auth import auth_router
from github_pm.context import context

router = APIRouter()


@router.get("/health")
async def health():
    return {"message": "OK"}


router.include_router(api_router, prefix="/api/v1")
router.include_router(auth_router, prefix="/api/v1/auth")

app = FastAPI(
    title="GitHub Project Management API",
    version="0.1.0",
)

# Add CORS middleware to allow frontend requests with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=context.session_secret,
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=False,  # Set to True in production with HTTPS
)

app.include_router(router)
