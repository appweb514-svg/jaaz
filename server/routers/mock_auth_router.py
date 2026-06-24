"""
Mock auth endpoints for local Jaaz usage (bypass cloud login)
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/device", tags=["auth"])

@router.post("/auth")
async def start_device_auth():
    """Mock device auth start"""
    return JSONResponse({
        "status": "pending",
        "code": "local-dev-code",
        "expires_at": "2099-12-31T23:59:59Z",
        "message": "Local mode - no auth needed"
    })

@router.get("/poll")
async def poll_device_auth(code: str = ""):
    """Mock device auth poll - always authorized"""
    return JSONResponse({
        "status": "authorized",
        "token": "local-dev-token",
        "user_info": {
            "id": "local-user",
            "username": "Local User",
            "email": "local@local.dev"
        }
    })

@router.get("/refresh-token")
async def refresh_token():
    """Mock token refresh"""
    return JSONResponse({
        "new_token": "local-dev-token-refreshed"
    })
