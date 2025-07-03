from fastapi import APIRouter
from schemas.requests_responses import HealthResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify the router is working.
    """
    return HealthResponse(
        status="ok", message="Health router is working", service="Computer Vision Verification API"
    )
