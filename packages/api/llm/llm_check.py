import os
import base64
import io
import asyncio
import logging
import json
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple, cast
import uuid
from PIL import Image
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, ValidationError

# Using callbacks instead of direct AIMessage handling
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult, ChatGeneration
from langchain_core.messages import BaseMessage, AIMessage  # For type hinting

from utils.llm import get_model


class TotalCheckItemResult(BaseModel):
    item_id: str = Field(..., description="The ID of the item being matched")
    file_ids: List[str] = Field(
        ...,
        description="The IDs of the files that match the item. the IDs will be located in the proceeding message before the file. Be extremely honest and critical of the chosen results",
    )
    image_found: bool = Field(
        ...,
        description="Whether at least one image was found that matches the description. Be extremely honest and critical of this result.",
    )
    reasoning: str = Field(
        ...,
        description="A complete image description, in the most verbose manner possible, matched against criteria of the item.  Be extremely honest and critical of this result.",
    )
    confidence: Optional[float] = Field(
        None,
        description="A score specifying how confident you are of the match, between 0.0 and 1.0. 0 is not confident at all. 0.5 is mildly confident. Anything greater than 0.8 is absolutely confident.",
    )  # Made Optional explicit
    # confidence: None
    location: Optional[str] = Field(
        None,
        description="Location found in the first image, if any. Do not add any other text, just the detected location.",
    )


class TotalCheckResponse(BaseModel):
    items: list[TotalCheckItemResult] = Field(
        ...,
        description="A list of the items that are being analyzed for and their matching (or not matching) filenames ",
    )


class ImageDescriptions(BaseModel):
    images: list[str] = Field(
        ...,
        description="A detailed description of each image that has been submitted. Be extremely detailed in your description.",
    )


class ImageCheckResponse(BaseModel):
    is_match: bool = Field(
        ..., description="Whether the image matches the description."
    )
    reasoning: str = Field(
        ...,
        description="Reasoning for the match or mismatch. Must be less than 20 words, or one sentence. Be very terse.",
    )
    confidence: Optional[float] = Field(
        None, description="Confidence score for the match, between 0.0 and 1.0."
    )
    location: Optional[str] = Field(
        None,
        description="Location found in the image, if any. Do not add any other text, just the detected location.",
    )


class ImageComparisonResponse(BaseModel):
    """Structured response for comparing two images based on criteria."""

    is_match: bool = Field(
        ...,
        description="Whether the two images conform to each other based on the provided criteria.",
    )
    reasoning: str = Field(
        ...,
        description="Reasoning for the match or mismatch based on the criteria. Must be less than 20 words, or one sentence.",
    )
    confidence: Optional[float] = Field(
        None, description="Confidence score for the match, between 0.0 and 1.0."
    )


# Define the callback handler for token usage
class TokenUsageCallbackHandler(AsyncCallbackHandler):
    """Async Callback handler to log and store Bedrock token usage."""

    def __init__(self):
        super().__init__()
        self.input_tokens = 0
        self.output_tokens = 0

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM ends running."""
        logger = logging.getLogger(__name__)  # Get logger instance
        print(f"LLM response from callback: {response}")  # Keep for debugging if needed

        # Attempt to extract usage metadata from the AIMessage within the ChatGeneration
        usage_metadata = None
        try:
            # Check if we have generations and the first generation is a ChatGeneration with an AIMessage
            if (
                response.generations
                and len(response.generations) > 0
                and len(response.generations[0]) > 0
                and isinstance(response.generations[0][0], ChatGeneration)
                and isinstance(response.generations[0][0].message, AIMessage)
                and hasattr(response.generations[0][0].message, "usage_metadata")
                and response.generations[0][0].message.usage_metadata is not None
            ):
                usage_metadata = response.generations[0][0].message.usage_metadata
                self.input_tokens = usage_metadata.get("input_tokens", 0)
                self.output_tokens = usage_metadata.get("output_tokens", 0)
                logger.info(
                    f"LLM Token Usage (run_id: {run_id}) - Input: {self.input_tokens}, Output: {self.output_tokens}"
                )
            else:
                logger.warning(
                    f"LLM response (run_id: {run_id}) did not contain usage_metadata in the expected location or is not a ChatGeneration."
                )
                self.input_tokens = 0
                self.output_tokens = 0
        except (AttributeError, IndexError, TypeError, KeyError) as e:
            logger.warning(
                f"Error accessing usage_metadata in LLM response (run_id: {run_id}): {e}. Response structure might be different than expected."
            )
            self.input_tokens = 0
            self.output_tokens = 0


# Define the return type for token usage
class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int

    def __init__(self, **data):
        super().__init__(**data)


async def llm_check_image(
    image_path: str, description: str
) -> Tuple[ImageCheckResponse, TokenUsage]:
    """
    Check if the image matches the provided description using a vision model.

    Args:
        image_path: Path to the image file
        description: Description to compare the image against

    Returns:
        ImageCheckResponse with match result and reasoning
    """

    # Instantiate the TokenUsage class directly
    default_token_usage = TokenUsage(input_tokens=0, output_tokens=0)

    # Verify the image exists
    if not os.path.exists(image_path):
        return ImageCheckResponse(
            is_match=False,
            reasoning=f"Image file not found at path: {image_path}",
            confidence=1.0,  # 100% confident that we can't match a non-existent image
            location=None,
        ), default_token_usage

    logger = logging.getLogger(__name__)
    logger.info(f"Processing image: {image_path}")

    # System prompt can be simplified as the output structure is handled by the model binding
    sys_prompt = """You are an expert at checking images against a specified description.
    Analyze the provided image and determine if it matches the given description.
    Do not speak in first person, and remain professional and concise.
    Provide your reasoning, confidence score, and any location identified in the image."""

    # Check image file size and process
    try:
        # Open with Pillow to verify it's a valid image and potentially resize
        with Image.open(image_path) as img:
            # img.verify()  # Verify image integrity before potentially resizing
            original_format = img.format  # Store original format for saving later

            max_width, max_height = 1024, 1024
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            # Use original format if known and supported, else default (e.g., JPEG)
            save_format = (
                original_format
                if original_format in ["JPEG", "PNG", "GIF", "WEBP"]
                else "JPEG"
            )
            img.save(buffer, format=save_format)
            image_data = buffer.getvalue()

    except FileNotFoundError:
        # This case is already handled by the os.path.exists check above, but good practice
        return ImageCheckResponse(
            is_match=False,
            reasoning=f"Image file not found at path: {image_path}",
            confidence=1.0,
            location=None,
        ), default_token_usage
    except Exception as e:
        # Catch potential Pillow errors or other issues during size check/opening
        return ImageCheckResponse(
            is_match=False,
            reasoning=f"Error processing image file: {str(e)}",
            confidence=1.0,
            location=None,
        ), default_token_usage

    # Encode the (potentially resized) image data
    base64_image = base64.b64encode(image_data).decode("utf-8")

    # Determine image format for Bedrock (using file extension as primary source)
    # This is separate from the format used for saving the resized image buffer
    bedrock_image_format_ext = Path(image_path).suffix.lstrip(".").lower()

    # Map common extensions to Bedrock-compatible media types
    bedrock_format_mapping = {
        "jpg": "jpeg",
        "jpeg": "jpeg",
        "png": "png",
        "gif": "gif",
        "webp": "webp",
    }

    # Default to png if no extension or unsupported format
    bedrock_media_type_suffix = bedrock_format_mapping.get(
        bedrock_image_format_ext, "png"
    )

    llm = get_model()
    # Bind the Pydantic model back for structured output
    structured_llm = llm.with_structured_output(ImageCheckResponse)
    # Instantiate the callback handler
    token_handler = TokenUsageCallbackHandler()

    # Simplified message structure
    messages: List[Dict[str, Any] | BaseMessage] = [
        {"role": "system", "content": sys_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Does this image match the following description?\n\nDescription:\n{description}",
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{bedrock_media_type_suffix}",
                        "data": base64_image,
                    },
                },
            ],
        },
    ]

    # Call the structured LLM with linear retry delay
    # 12 minutes 💀
    max_retries = 240
    fixed_delay = 5  # Fixed delay in seconds

    retry_count = 0
    while True:
        try:
            # Invoke the structured LLM, passing the callback handler in the config
            # The handler will log token usage automatically via on_llm_end
            llm_response = await structured_llm.ainvoke(
                messages, config={"callbacks": [token_handler]}
            )
            response = cast(ImageCheckResponse,llm_response)

            # Log the structured response itself (token usage logged by callback)
            logger.info(f"Parsed LLM response: {response.model_dump()}")

            # Ensure confidence is within bounds if provided
            if response.confidence is not None:
                response.confidence = max(0.0, min(1.0, response.confidence))

            # Retrieve token usage from the handler
            token_usage = TokenUsage(
                input_tokens=token_handler.input_tokens,
                output_tokens=token_handler.output_tokens,
            )
            logger.info(f"Token usage: {token_usage}")
            return (
                response,
                token_usage,
            )  # Return the structured response and token usage

        except Exception as e:
            # Check if it's a throttling or other retryable exception
            # NOTE: Parsing errors from structured output are often raised here too
            error_code = None
            is_throttling = False
            if isinstance(e, ClientError):
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "ThrottlingException":
                    is_throttling = True
            elif (
                "ThrottlingException" in str(e)
                or "TooManyRequestsException" in str(e)
                or "Rate exceeded" in str(e)
            ):
                is_throttling = True
            # Also consider potential parsing errors from structured output as retryable
            # Langchain's structured output might raise errors that contain these strings
            elif (
                "Could not parse tool invocation" in str(e)
                or "Failed to parse" in str(e)
                or isinstance(e, (json.JSONDecodeError, ValidationError))
            ):  # Explicitly catch parsing errors
                is_throttling = (
                    True  # Treat parsing errors like throttling for retry purposes
                )

            if is_throttling:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) exceeded when calling Bedrock API. Last error: {str(e)}"
                    )
                    # Return a default error response instead of raising
                    return ImageCheckResponse(
                        is_match=False,
                        reasoning=f"Failed to get LLM response after {max_retries} retries. Last error: {str(e)}",
                        confidence=0.0,
                        location=None,
                    ), default_token_usage  # Return default tokens on max retries

                # Use fixed delay instead of exponential backoff
                delay = fixed_delay
                logger.warning(
                    f"Bedrock API throttled or parsing error. Retrying in {delay} seconds (attempt {retry_count}/{max_retries}). Error: {str(e)}"
                )
                await asyncio.sleep(delay)
            else:
                # Not a retryable exception
                logger.error(f"Non-retryable error calling Bedrock API: {str(e)}")
                # Return a default error response
                return ImageCheckResponse(
                    is_match=False,
                    reasoning=f"Non-retryable error calling LLM: {str(e)}",
                    confidence=0.0,
                    location=None,
                ), default_token_usage  # Return default tokens on non-retryable error


# --- Helper function to process image bytes ---
async def _process_image_bytes(
    image_bytes: bytes, image_source_description: str
) -> Tuple[Optional[str], Optional[str]]:
    """Processes image bytes: resizes, encodes, determines media type."""
    logger = logging.getLogger(__name__)
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            original_format = img.format
            max_width, max_height = 1024, 1024
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            save_format = (
                original_format
                if original_format in ["JPEG", "PNG", "GIF", "WEBP"]
                else "JPEG"
            )
            img.save(buffer, format=save_format)
            processed_image_data = buffer.getvalue()

            base64_image = base64.b64encode(processed_image_data).decode("utf-8")

            # Determine media type based on original format if possible
            bedrock_format_mapping = {
                "JPEG": "jpeg",
                "PNG": "png",
                "GIF": "gif",
                "WEBP": "webp",
            }
            # Default to jpeg if format unknown/unsupported
            bedrock_media_type_suffix = bedrock_format_mapping.get(
                original_format or "UNKNOWN", "jpeg"
            )

            return base64_image, f"image/{bedrock_media_type_suffix}"

    except Exception as e:
        logger.error(
            f"Error processing image bytes from {image_source_description}: {str(e)}"
        )
        return None, None


async def llm_compare_images(
    image1_bytes: bytes, image2_bytes: bytes, criteria: str
) -> Tuple[ImageComparisonResponse, TokenUsage]:
    """
    Compares two images based on specified criteria using a vision model.

    Args:
        image1_bytes: Bytes of the first image.
        image2_bytes: Bytes of the second image.
        criteria: The criteria text to use for comparison.

    Returns:
        A tuple containing:
        - ImageComparisonResponse: Match result, reasoning, confidence.
        - TokenUsage: Input and output token counts.
    """
    logger = logging.getLogger(__name__)
    default_token_usage = TokenUsage(input_tokens=0, output_tokens=0)
    default_error_response = ImageComparisonResponse(
        is_match=False,
        reasoning="Error during image comparison process.",
        confidence=0.0,
    )

    # Process both images
    base64_image1, media_type1 = await _process_image_bytes(image1_bytes, "image 1")
    base64_image2, media_type2 = await _process_image_bytes(image2_bytes, "image 2")

    if not base64_image1 or not media_type1 or not base64_image2 or not media_type2:
        logger.error("Failed to process one or both images for comparison.")
        return default_error_response, default_token_usage

    sys_prompt = """You are an expert at comparing two images based on specific criteria.
    Analyze the two provided images and determine if they conform to each other according to the given criteria.
    Focus solely on the relationship between the images as defined by the criteria.
    Do not speak in first person, and remain professional and concise.
    Provide your reasoning and confidence score."""

    llm = get_model()
    structured_llm = llm.with_structured_output(ImageComparisonResponse)
    token_handler = TokenUsageCallbackHandler()

    messages: List[Dict[str, Any] | BaseMessage] = [
        {"role": "system", "content": sys_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Compare Image 1 and Image 2. Do they conform to each other based on the following criteria?\n\nCriteria:\n{criteria}",
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type1,
                        "data": base64_image1,
                    },
                },
                {"type": "text", "text": "\n\nImage 2:"},  # Separator text
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type2,
                        "data": base64_image2,
                    },
                },
            ],
        },
    ]

    # Retry logic (similar to llm_check_image)
    max_retries = 240
    fixed_delay = 5
    retry_count = 0

    while True:
        try:
            llm_response = await structured_llm.ainvoke(
                messages, config={"callbacks": [token_handler]}
            )
            response = cast(ImageComparisonResponse, llm_response)
            logger.info(f"Parsed LLM comparison response: {response.model_dump()}")

            if response.confidence is not None:
                response.confidence = max(0.0, min(1.0, response.confidence))

            token_usage = TokenUsage(
                input_tokens=token_handler.input_tokens,
                output_tokens=token_handler.output_tokens,
            )
            logger.info(f"Comparison token usage: {token_usage}")
            return response, token_usage

        except Exception as e:
            error_code = None
            is_throttling = False
            if isinstance(e, ClientError):
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "ThrottlingException":
                    is_throttling = True
            elif (
                "ThrottlingException" in str(e)
                or "TooManyRequestsException" in str(e)
                or "Rate exceeded" in str(e)
            ):
                is_throttling = True
            elif (
                "Could not parse tool invocation" in str(e)
                or "Failed to parse" in str(e)
                or isinstance(e, (json.JSONDecodeError, ValidationError))
            ):
                is_throttling = True  # Treat parsing errors like throttling

            if is_throttling:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) exceeded for image comparison. Last error: {str(e)}"
                    )
                    return default_error_response, default_token_usage

                delay = fixed_delay
                logger.warning(
                    f"Bedrock API throttled or parsing error during comparison. Retrying in {delay} seconds (attempt {retry_count}/{max_retries}). Error: {str(e)}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Non-retryable error during image comparison: {str(e)}")
                return default_error_response, default_token_usage

    logger.error("Exited comparison retry loop unexpectedly.")
    return default_error_response, default_token_usage
