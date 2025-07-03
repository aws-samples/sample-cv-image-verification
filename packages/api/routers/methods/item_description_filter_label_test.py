import os
import logging
from typing import List
from schemas.requests_responses import (
    TestLabelFilteringRuleRequest,
    TestLabelFilteringRuleResponse,
    TestLabelFilteringRuleLabel,
)
from item_processing.aws_helpers import get_image_bytes_from_s3, detect_labels_s3
from strands import Agent
from strands.tools.tools import PythonAgentTool,ToolSpec

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get S3 bucket name from environment variable
STORAGE_BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME") or ""

if not STORAGE_BUCKET_NAME:
    logger.error("STORAGE_BUCKET_NAME environment variable not set.")
    # Raise an error as the bucket name is essential
    raise ValueError("S3 bucket name not configured in environment variables")


async def item_label_filter_rule_test(
    request: TestLabelFilteringRuleRequest,
) -> TestLabelFilteringRuleResponse:
    """
    Test the Item label filtering rule by detecting labels for given S3 image keys.

    Fetches images from S3, runs Rekognition label detection, and returns the results.
    """
    labels: List[TestLabelFilteringRuleLabel] = []
    image_keys = request.image_s3_keys or []  # Ensure it's a list

    logger.info(f"Starting label detection test for {len(image_keys)} image keys.")

    for s3_key in image_keys:
        try:
            logger.debug(f"Fetching image bytes for key: {s3_key}")
            image_bytes = await get_image_bytes_from_s3(STORAGE_BUCKET_NAME, s3_key)

            if image_bytes:
                logger.debug(f"Detecting labels for key: {s3_key}")
                detected_labels = await detect_labels_s3(image_bytes=image_bytes,resize_image=True)
                for label in detected_labels:
                    if label.get("Confidence", 0) > 70:
                        # Only consider labels with confidence greater than 70
                        labels.append(
                            TestLabelFilteringRuleLabel(
                                name=label["Name"],
                                confidence=label["Confidence"]
                                / 100.0,  # Convert percentage to decimal
                                s3_key=s3_key,
                            )
                        )
                logger.debug(f"Detected {len(labels)} labels for key: {s3_key}")
            else:
                logger.warning(f"Could not retrieve image bytes for key: {s3_key}")

        except Exception as e:
            logger.error(f"Error processing key {s3_key}: {e}", exc_info=True)

    logger.info("Label detection test completed.")
    logger.info(f"Detected {len(labels)} labels across {len(image_keys)} images.")
    return TestLabelFilteringRuleResponse(labels=labels)
