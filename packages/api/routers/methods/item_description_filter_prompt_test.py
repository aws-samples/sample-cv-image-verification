from item_processing.item_processor import call_using_all_files_raw
from schemas.requests_responses import (
    TestDescriptionFilterPromptRequest,
    TestDescriptionFilterPromptResponse,
)


async def item_description_filter_prompt_test(
    request: TestDescriptionFilterPromptRequest,
) -> TestDescriptionFilterPromptResponse:
    """
    Test the Item description filtering prompt with a given description and image S3 keys.
    """

    response = await call_using_all_files_raw(
        [request.description], [{"id": k, "s3_key": k} for k in request.image_s3_keys],agent_ids=request.agent_ids or [],search_internet=request.search_internet
    )
    return TestDescriptionFilterPromptResponse(response=response)
