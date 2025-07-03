from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel
from utils.config_helpers import (
    save_system_prompt,
    save_model_id,
    get_system_prompt,
    get_model_id,
    load_config_history,
    save_verification_job_second_pass,
    get_verification_job_second_pass,
    CONFIG_TYPE_SYSTEM_PROMPT,
    CONFIG_TYPE_MODEL_ID,
)

router = APIRouter()


class ConfigResponse(BaseModel):
    config_type: str
    timestamp: int
    value: str
    created_at: str
    is_active: str
    description: Optional[str] = None


class SystemPromptRequest(BaseModel):
    prompt: str
    description: Optional[str] = None


class ModelIdRequest(BaseModel):
    model_id: str
    description: Optional[str] = None


class VerificationJobSecondPassRequest(BaseModel):
    second_pass: bool
    description: Optional[str] = None


@router.get("/system-prompt", response_model=str)
async def get_current_system_prompt():
    """
    Get the current active system prompt.
    """
    return get_system_prompt()


@router.post("/system-prompt", response_model=ConfigResponse)
async def update_system_prompt(request: SystemPromptRequest):
    """
    Update the system prompt configuration.
    """
    result = save_system_prompt(request.prompt, request.description)
    return result


@router.get("/model-id", response_model=str)
async def get_current_model_id():
    """
    Get the current active model ID.
    """
    return get_model_id()


@router.post("/model-id", response_model=ConfigResponse)
async def update_model_id(request: ModelIdRequest):
    """
    Update the model ID configuration.
    """
    result = save_model_id(request.model_id, request.description)
    return result


@router.get("/second-pass", response_model=bool)
async def get_job_second_pass():
    """
    Returns a boolean indicating whether a second pass verification should be performed on images. A second verification pass executed on images helps reduce false positives in image verification, but makes verification jobs cost more and take longer to complete.
    """
    return get_verification_job_second_pass()


@router.post("/second-pass", response_model=ConfigResponse)
async def update_job_second_pass(request: VerificationJobSecondPassRequest):
    """
    Update the second pass configuration.
    """
    result = save_verification_job_second_pass(
        str(request.second_pass), request.description
    )
    return result


@router.get("/history/system-prompt", response_model=List[ConfigResponse])
async def get_system_prompt_history(limit: int = 10):
    """
    Get the history of system prompt configurations.
    """

    return load_config_history(CONFIG_TYPE_SYSTEM_PROMPT, limit)


@router.get("/history/model-id", response_model=List[ConfigResponse])
async def get_model_id_history(limit: int = 10):
    """
    Get the history of model ID configurations.
    """
    return load_config_history(CONFIG_TYPE_MODEL_ID, limit)
