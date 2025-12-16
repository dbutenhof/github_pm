from fastapi import APIRouter, FastAPI

from github_pm.api import api_router

router = APIRouter()


@router.get("/health")
async def health():
    return {"message": "OK"}


router.include_router(api_router, prefix="/api/v1")

app = FastAPI(
    title="GitHub Project Management API",
    version="0.1.0",
)

app.include_router(router)
