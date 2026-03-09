from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    stores,
    data_upload,
    owner,
    supervisor,
    hq,
    marketing,
    analysis,
    reports,
    settings,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(stores.router, prefix="/stores", tags=["stores"])
api_router.include_router(data_upload.router, prefix="/data", tags=["data-upload"])
api_router.include_router(owner.router, prefix="/owner", tags=["owner"])
api_router.include_router(supervisor.router, prefix="/supervisor", tags=["supervisor"])
api_router.include_router(hq.router, prefix="/hq", tags=["hq"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
