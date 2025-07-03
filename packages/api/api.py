from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import routers
from routers import (
    health,
    item_router,
    collections_router,
    verification_job_router,
    llm_config,
    agents_router,
)
# from app.routers import items, users

app = FastAPI(
    title="Computer Vision Image Verification API",
    description="FastAPI backend for the Computer Vision Image Verification sample.",
    version="0.1.0",
    terms_of_service="https://aws.amazon.com/asl/",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["CVImageVerification"])
app.include_router(item_router.router, prefix="/items", tags=["CVImageVerification"])
app.include_router(
    collections_router.router, prefix="/collections", tags=["CVImageVerification"]
)
app.include_router(
    verification_job_router.router,
    prefix="/verification-jobs",
    tags=["CVImageVerification"],
)
app.include_router(llm_config.router, prefix="/llm-config", tags=["CVImageVerification"])
app.include_router(agents_router.router, prefix="/agents", tags=["CVImageVerification"])


@app.get("/", tags=["CVImageVerification"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok", "message": "API is running"}


# Handler for AWS Lambda
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    # Use import string for multi-worker support or reload
    # Note: workers > 1 is primarily for CPU-bound tasks locally,
    # and doesn't affect Lambda deployment via Mangum.
    # Set reload=True if needed for development auto-reloading.
    uvicorn.run("api:app", host="0.0.0.0", port=8000, workers=4, reload=True)
