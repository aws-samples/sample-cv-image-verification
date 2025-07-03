import asyncio
import io
import json
import os
import math
import tempfile
import time
from llm.llm_check import (
    TokenUsage,
    TokenUsageCallbackHandler,
    TotalCheckResponse,
)
from item_processing.agents import augment_item_description
from utils.config_helpers import (
    get_second_pass_verification_system_prompt,
    get_system_prompt,
)
from schemas.datamodel import ItemInstance, CollectionFile, VerificationJob
from PIL import Image
from botocore.exceptions import ClientError
from typing import Any, Tuple, cast
from pydantic import BaseModel, ValidationError
from constants import STORAGE_BUCKET_NAME
from .aws_helpers import get_image_bytes_from_s3
from utils.llm import get_model, create_system_message


def create_image_grid(images, grid_size, max_grid_dimension=2000, index_total=0):
    """Create a grid of images with ID labels"""
    rows, cols = grid_size
    image_spacing = 40
    cell_width = max_grid_dimension // cols
    label_height = int(max_grid_dimension // rows * 0.25)
    image_height = max_grid_dimension // rows - label_height
    cell_height = image_height + label_height

    grid_img = Image.new(
        "RGB", (cell_width * cols, cell_height * rows), color=(0, 0, 0)
    )

    image_positions = {}
    from PIL import ImageDraw

    draw = ImageDraw.Draw(grid_img)

    # Create thatched pattern background
    for y in range(0, cell_height * rows, 10):
        for x in range(0, cell_width * cols, 10):
            draw.line([(x, y), (x + 5, y + 5)], fill=(200, 200, 200), width=1)
            draw.line([(x + 5, y), (x, y + 5)], fill=(200, 200, 200), width=1)

    font_size = max(96, 96)

    # Place each image in the grid
    for idx, (img, image_id) in enumerate(images):
        if idx >= rows * cols:
            break

        row = idx // cols
        col = idx % cols

        # Calculate cell boundaries
        rect_x0 = col * cell_width
        rect_y0 = row * cell_height
        rect_x1 = rect_x0 + cell_width - 1
        rect_y1 = rect_y0 + cell_height - 1

        # Calculate content area
        content_x0 = rect_x0 + image_spacing
        content_y0 = rect_y0 + image_spacing
        content_x1 = rect_x1 - image_spacing
        content_y1 = rect_y0 + image_height - image_spacing

        content_width = content_x1 - content_x0
        content_height = content_y1 - content_y0
        label_y = row * cell_height + image_height

        # Create a white background for the image and label
        draw.rectangle(
            [content_x0, content_y0, content_x1, rect_y1 - image_spacing], fill="black"
        )

        # Resize the image to fit
        img_copy = img.copy()
        try:
            img_copy.thumbnail((content_width, content_height), Image.Resampling.LANCZOS)
        except AttributeError:
            # Fallback for older PIL versions
            img_copy.thumbnail((content_width, content_height))

        # Center the image
        x_offset = content_x0 + (content_width - img_copy.width) // 2
        y_offset = content_y0 + (content_height - img_copy.height) // 2

        grid_img.paste(img_copy, (x_offset, y_offset))

        # Add ID text
        id_text = f"ID: {idx + index_total}"
        text_width = draw.textlength(id_text, font_size=font_size)
        text_x = col * cell_width + (cell_width - text_width) // 2
        text_y = label_y + (label_height - font_size) // 2
        draw.text((text_x, text_y), id_text, fill="white", font_size=font_size)

        image_positions[str(idx + index_total)] = image_id

        # Draw a rectangle around the image and its label
        rect_x0 = col * cell_width
        rect_y0 = row * cell_height
        rect_x1 = rect_x0 + cell_width - 1
        rect_y1 = rect_y0 + cell_height - 1
        draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], outline="black", width=1)

    grid_img.save(f"/tmp/grid_image{str(time.time())}.jpeg")
    return grid_img, image_positions


async def _load_and_process_image(
    image_info: dict, storage_bucket_name: str
) -> Tuple[Image.Image | None, str | None, str | None]:
    """Loads image from S3, returns Pillow image, ID, and temp path"""
    image_bytes = await get_image_bytes_from_s3(
        storage_bucket_name, image_info["s3_key"]
    )
    image_path = ""
    if image_bytes is None:
        return None, image_info.get("id"), None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", mode="wb") as tf:
            tf.write(image_bytes)
            image_path = tf.name
        img = Image.open(image_path)
        img.load()
        return img, image_info.get("id"), image_path
    except Exception:
        if image_path and os.path.exists(image_path):
            try:
                os.unlink(image_path)
            except Exception:
                pass
        return None, image_info.get("id"), None


async def _process_images_and_call_llm(
    messages: list[Any],
    initial_contents: list[Any],
    image_sources: list[dict],
    max_images_per_message: int,
    max_retries: int,
    fixed_delay: int,
) -> Tuple[TotalCheckResponse, TokenUsage, Any]:
    """Handles image processing and LLM invocation with retries"""
    contents = initial_contents[:]
    temp_image_paths_to_clean = []
    loaded_images_map = {}
    image_ids: list[str] = []
    try:
        # Grid Image Logic
        images_per_grid = math.ceil(len(image_sources) / max_images_per_message)

        # Load all images first
        loaded_images_data = await asyncio.gather(
            *[
                _load_and_process_image(img_info, STORAGE_BUCKET_NAME)
                for img_info in image_sources
            ]
        )

        # Filter out failed loads
        loaded_images = []
        for img, img_id, img_path in loaded_images_data:
            image_ids.append(img_id or "")
            if img and img_path:
                loaded_images.append((img, img_id, img_path))
                temp_image_paths_to_clean.append(img_path)
                loaded_images_map[img_path] = img
            elif img_path:
                temp_image_paths_to_clean.append(img_path)

        grid_count = min(
            max_images_per_message,
            math.ceil(len(loaded_images) / max(images_per_grid, 1)),
        )
        grid_size_sqrt = int(math.sqrt(images_per_grid))
        grid_rows = grid_size_sqrt
        grid_cols = math.ceil(images_per_grid / grid_rows)

        positions = {}

        for i in range(grid_count):
            start_idx = i * images_per_grid
            end_idx = min(start_idx + images_per_grid, len(loaded_images))
            grid_images_data = [
                (img, img_id) for img, img_id, _ in loaded_images[start_idx:end_idx]
            ]

            if not grid_images_data:
                continue

            grid_img, image_positions = create_image_grid(
                grid_images_data, (grid_rows, grid_cols), 2000, start_idx
            )

            positions.update(image_positions)

            buffer = io.BytesIO()
            grid_img.save(buffer, format="JPEG")
            image_data = buffer.getvalue()
            grid_img.close()

            contents.append(
                {"image": {"format": "jpeg", "source": {"bytes": image_data}}}
            )

            # if messages and messages[-1]["role"] == "user":
            #     messages.append({"role": "assistant", "content": "Awaiting images..."})
            # messages.append({"role": "user", "content": contents})
            # contents = []
        messages.append({"role": "user", "content": contents})
        # LLM Call Logic
        retry_count = 0
        llm = get_model()
        structured_llm = llm.with_structured_output(TotalCheckResponse)
        token_handler = TokenUsageCallbackHandler()
        default_token_usage = TokenUsage(input_tokens=0, output_tokens=0)

        while True:
            try:
                response = await structured_llm.ainvoke(
                    messages, config={"callbacks": [token_handler]}
                )
                # Ensure the response is the expected type
                if not isinstance(response, TotalCheckResponse):
                    raise ValueError(f"Expected TotalCheckResponse, got {type(response)}")
                token_usage = TokenUsage(
                    input_tokens=token_handler.input_tokens,
                    output_tokens=token_handler.output_tokens,
                )
                return response, token_usage, positions

            except Exception as e:
                is_throttling = False
                if isinstance(e, ClientError):
                    error_code = cast(ClientError,e).response.get("Error", {}).get("Code")
                    if error_code == "ThrottlingException":
                        is_throttling = True
                elif (
                    "ThrottlingException" in str(e)
                    or "TooManyRequestsException" in str(e)
                    or "Rate exceeded" in str(e)
                    or "Could not parse tool invocation" in str(e)
                    or "Failed to parse" in str(e)
                    or isinstance(e, (json.JSONDecodeError, ValidationError))
                ):
                    is_throttling = True

                if is_throttling:
                    retry_count += 1
                    if retry_count > max_retries:
                        error_response = TotalCheckResponse(items=[])
                        return error_response, default_token_usage, positions
                    await asyncio.sleep(fixed_delay)
                else:
                    error_response = TotalCheckResponse(items=[])
                    return error_response, default_token_usage, positions
    finally:
        # Cleanup Temporary Files and Close Images
        for _path, img in loaded_images_map.items():
            try:
                img.close()
            except Exception:
                pass

        for path in temp_image_paths_to_clean:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass


class CallUsingAllFilesResponse(BaseModel):
    """Response model for the call_using_all_files function"""

    response: TotalCheckResponse
    token_usage: TokenUsage


async def call_second_pass_verification(
    item_description: str, file_sources: list[dict]
) -> CallUsingAllFilesResponse:
    """Calls the LLM with raw descriptions and file sources"""

    system_prompt = get_second_pass_verification_system_prompt()
    messages: list[Any] = [create_system_message(system_prompt)]

    contents: list[Any] = []
    contents.append(
        {
            "type": "text",
            "text": f"""Here is the item information: {item_description}""",
        },
    )

    # Configuration
    MAX_IMAGES_PER_MESSAGE = 20
    MAX_RETRIES = 240
    FIXED_DELAY = 5

    # Call the helper function
    response, token_usage, positions = await _process_images_and_call_llm(
        messages=messages,
        initial_contents=contents,
        image_sources=file_sources,
        max_images_per_message=MAX_IMAGES_PER_MESSAGE,
        max_retries=MAX_RETRIES,
        fixed_delay=FIXED_DELAY,
    )

    return CallUsingAllFilesResponse(response=response, token_usage=token_usage)


async def call_using_all_files_raw(
    descriptions: list[str],
    file_sources: list[dict],
    agent_ids: list[str] = [],
    search_internet: bool = False,
) -> CallUsingAllFilesResponse:
    """
    Calls the LLM with raw descriptions and file sources.
    This function processes a list of item descriptions along with associated file sources,
    optionally augments the descriptions using specified agents, and sends them to the
    language learning model (LLM) for processing.
    Args:
        descriptions (list[str]): A list of text descriptions of items to be processed.
        file_sources (list[dict]): A list of dictionaries containing source information for files
            (typically images) associated with the items.
        agent_ids (list[str], optional): IDs of agents to be used for augmenting the item descriptions.
            If empty, no augmentation is performed. Defaults to [].
        search_internet (bool, optional): Whether to allow internet search during description 
            augmentation. Only applies if agent_ids is not empty. Defaults to False.
    Returns:
        CallUsingAllFilesResponse: An object containing the LLM's response and token usage information.
            - response: The generated response from the LLM.
            - token_usage: Information about the tokens used in the process.
    Note:
        The function has built-in retry logic and handles batching of images to prevent
        exceeding API limits.
    """
    items_desc = [f"Item description: {desc}" for desc in descriptions]
    if len(agent_ids)>0:
        # Run the augmentation function for each description
        items_desc = await asyncio.gather(*[augment_item_description(item_description=desc,agent_ids=agent_ids,search_internet=search_internet) for desc in descriptions])
        
    system_prompt = get_system_prompt()
    messages: list[Any] = [create_system_message(system_prompt)]

    contents: list[Any] = []
    items_text = "\n".join(items_desc)
    contents.append(
        {
            "type": "text",
            "text": f'''Here is the list of items 
            <Items>
{items_text}
 </Items>''',
        },
    )

    print(contents)
    # Configuration
    MAX_IMAGES_PER_MESSAGE = 20
    MAX_RETRIES = 240
    FIXED_DELAY = 5

    # Call the helper function
    response, token_usage, positions = await _process_images_and_call_llm(
        messages=messages,
        initial_contents=contents,
        image_sources=file_sources,
        max_images_per_message=MAX_IMAGES_PER_MESSAGE,
        max_retries=MAX_RETRIES,
        fixed_delay=FIXED_DELAY,
    )

    return CallUsingAllFilesResponse(response=response, token_usage=token_usage)


async def call_using_all_files(
    job:VerificationJob, item_instances:list[ItemInstance],collection_files: list[CollectionFile]
) -> Tuple[TotalCheckResponse, TokenUsage, Any]:
    """
    Calls a language model with item instances and collection files for verification.

    This function processes a list of items and their descriptions, combines them with
    collection files (images), and makes calls to a language model to analyze the data.
    It handles batching of images to stay within API limits.

    Args:
        job (VerificationJob): The verification job containing settings like search_internet.
        item_instances (list[ItemInstance]): A list of items to be processed and verified.
        collection_files (list[CollectionFile]): A list of files (primarily images) to be analyzed.
        
    Returns:
        Tuple[TotalCheckResponse, TokenUsage, Any]: A tuple containing:
            - The language model's response for item verification
            - Token usage information from the API call
            - Position information of the analyzed elements
    """
    
    items_desc = []
    for item in item_instances:
        # Ensure description_filtering_rules_applied exists and is iterable
        descriptions = (
            item.description_filtering_rules_applied
            if item.description_filtering_rules_applied
            else []
        )
        if not isinstance(descriptions, list):
            descriptions_text = "N/A"
        else:
            descs = [desc.description for desc in descriptions]
            descriptions_text = ", ".join(descs) if descs else "N/A"
            if descs and item.agent_ids and len(item.agent_ids) > 0:
                descriptions_text = await augment_item_description(search_internet=job.search_internet or False,item_description=descriptions_text,agent_ids=item.agent_ids or [])
              
        items_desc.append(f"""
Item id: {item.id}
Item description: {item.name} - {item.description} . {descriptions_text}
    """)

    system_prompt = get_system_prompt()
    messages: list[Any] = [create_system_message(system_prompt)]

    contents: list[Any] = []
    items_text = "\n".join(items_desc)
    contents.append(
        {
            "type": "text",
            "text": f"""Here is the list of items. We are looking for images that match these items, these images may not be present, so do not make up any details that are not accurately displayed within the images
<Items>
{items_text}
</Items>""",
        },
    )
    # print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    # print(contents)
    # print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    # Configuration
    MAX_IMAGES_PER_MESSAGE = 20
    MAX_RETRIES = 240
    FIXED_DELAY = 5

    # Ensure work_order_files are dicts for the helper function
    image_sources = [dict(file) for file in collection_files]

    # Call the helper function
    response, token_usage, positions = await _process_images_and_call_llm(
        messages=messages,
        initial_contents=contents,
        image_sources=image_sources,
        max_images_per_message=MAX_IMAGES_PER_MESSAGE,
        max_retries=MAX_RETRIES,
        fixed_delay=FIXED_DELAY,
    )

    return response, token_usage, positions
