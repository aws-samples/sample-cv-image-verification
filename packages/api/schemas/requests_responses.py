from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from schemas.datamodel import AddressSuggestion, AssessmentStatus, Collection, CollectionFile, DescriptionFilteringRule, Item, LabelFilteringRule, VerificationJob, VerificationJobDto, VerificationJobLogEntry, Agent
from item_processing.item_processor import CallUsingAllFilesResponse


# Health Router Models
class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str
    message: str
    service: str
class ItemListResponse(BaseModel):
    """
    Response model for listing items.
    
    Returns a paginated list of Item objects that match the query criteria.
    """

    items: List[Item]

class CollectionsListResponse(BaseModel):
    """
    Response model for listing collections.
    
    Returns a paginated list of Collection objects available to the user,
    including their metadata and associated files.
    """

    items: List[Collection]


class CollectionResponse(BaseModel):
    """
    Response model for retrieving a single collection.
    
    Returns detailed information about a specific collection including
    all associated files, items, and metadata.
    """
    collection: Collection


class CreateCollectionRequest(BaseModel):
    """
    Request model for creating a new collection.
    
    Contains the initial configuration for a collection including optional
    description, files, assessment status, address, and associated item IDs.
    """
    description: Optional[str] = None
    files: List[CollectionFile] = []
    status: AssessmentStatus = AssessmentStatus.PENDING
    address: Optional[str] = None
    item_ids: List[str] = []


class CreateCollectionResponse(BaseModel):
    """
    Response model for collection creation.
    
    Returns the newly created collection with its assigned ID and
    any system-generated metadata.
    """
    collection: Collection


class UpdateCollectionRequest(BaseModel):
    """
    Request model for updating an existing collection.
    
    All fields are optional, allowing partial updates to collection properties
    including description, files, status, and address information.
    """
    description: Optional[str] = None
    files: Optional[List[CollectionFile]] = None
    status: Optional[AssessmentStatus] = None
    address: Optional[str] = None


class UpdateCollectionResponse(BaseModel):
    """
    Response model for collection updates.
    
    Returns the updated collection with all current values after
    the modification has been applied.
    """
    collection: Collection

class PresignUploadResponse(BaseModel):
    """Response model for generating a presigned URL for file upload."""

    presigned_url: str
    file_metadata: Dict[str, Any]
class AddFileRequest(BaseModel):
    """Request model for adding a file to a collection."""

    id: str
    created_at: int
    s3_key: str
    description: Optional[str] = None
    content_type: str
    filename: str
    status: Optional[AssessmentStatus] = None
    status_reasoning: Optional[str] = None


class AddFileResponse(BaseModel):
    """
    Response model for adding a file to a collection.
    
    Returns the updated collection containing the newly added file
    along with any generated metadata.
    """
    collection: Collection


class CollectionFilePresignedUrlsResponse(BaseModel):
    """Response model containing presigned URLs for collection files."""

    presigned_urls: Dict[str, str] = Field(
        ..., description="Dictionary mapping file IDs to their presigned GET URLs"
    )

class CreateLabelFilteringRuleRequest(BaseModel):
    """Request model for creating a label filtering rule."""

    image_label: str
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    min_image_size_percent: float = Field(..., ge=0.0, le=1.0)
    exclude: bool = False


class UpdateLabelFilteringRuleRequest(BaseModel):
    """Request model for updating a label filtering rule."""

    image_label: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_image_size_percent: Optional[float] = Field(None, ge=0.0, le=1.0)
    exclude: Optional[bool] = None

class CreateItemInstanceRequest(BaseModel):
    """Request model for creating an item instance."""

    name: str
    description: str
    filtering_rules_applied: List[LabelFilteringRule] = []
    assessment_reasoning: Optional[str] = None
    status: AssessmentStatus = AssessmentStatus.PENDING


class UpdateItemInstanceRequest(BaseModel):
    """
    Request model for updating an item instance.
    
    Allows partial updates to item instance properties including name,
    description, applied filtering rules, assessment reasoning, and status.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    filtering_rules_applied: Optional[List[LabelFilteringRule]] = None
    assessment_reasoning: Optional[str] = None
    status: Optional[AssessmentStatus] = None

class CreateItemRequest(BaseModel):
    """Request model for creating a new item."""

    name: str
    description: str
    label_filtering_rules: List[LabelFilteringRule] = []
    description_filtering_rules: Optional[List[DescriptionFilteringRule]] = None
    cluster_number: Optional[int] = None
    agent_ids: Optional[list[str]] = Field(
        None, description="Optional list of agent IDs associated with the item"
    )


class UpdateItemRequest(BaseModel):
    """Request model for updating an existing item."""

    name: Optional[str] = None
    description: Optional[str] = None
    label_filtering_rules: Optional[List[LabelFilteringRule]] = None
    description_filtering_rules: Optional[List[DescriptionFilteringRule]] = None
    cluster_number: Optional[int] = None
    agent_ids: Optional[list[str]] = Field(
        [], description="Optional list of agent IDs associated with the item"
    )

# Verification Job Models
class VerificationJobListResponse(BaseModel):
    """Response model for listing verification jobs."""

    items: List[VerificationJob]


class VerificationJobResponse(BaseModel):
    """Response model for retrieving a single verification job."""
    verification_job: VerificationJobDto


class CreateVerificationJobRequest(BaseModel):
    """Request model for creating a verification job."""

    collection_id: str
    status: AssessmentStatus = AssessmentStatus.PENDING
    confidence: Optional[float] = None
    search_internet: bool = Field(
        False, description="Whether to search the internet for additional information during verification")


class CreateVerificationJobResponse(BaseModel):
    """Response model for creating a verification job."""

    verification_job: VerificationJob


class UpdateVerificationJobRequest(BaseModel):
    """Request model for updating a verification job."""

    status: Optional[AssessmentStatus] = None
    confidence: Optional[float] = None
    search_internet: bool = Field(
        False, description="Whether to search the internet for additional information during verification")


class UpdateVerificationJobResponse(BaseModel):
    """Response model for updating a verification job."""

    verification_job: VerificationJob


class VerificationJobFilePresignedUrlsResponse(BaseModel):
    """Response model containing presigned URLs for verification job files."""

    presigned_urls: Dict[str, str] = Field(
        ..., description="Dictionary mapping file IDs to their presigned GET URLs"
    )


# --- Address Autocomplete ---
class AddressAutocompleteResponse(BaseModel):
    """Response model for address autocomplete suggestions."""

    suggestions: List[AddressSuggestion]


# --- Verification Job Log Models ---
class VerificationJobLogListResponse(BaseModel):
    """Response model for listing verification job log entries with pagination."""

    items: List[VerificationJobLogEntry]
    last_evaluated_key: Optional[Dict[str, Any]] = Field(
        None,
        description="The key to use for fetching the next page of results, if any.",
    )


class GenerateUploadUrlsRequest(BaseModel):
    """
    Request model for generating multiple presigned upload URLs.
    
    Takes a list of filenames and generates corresponding presigned URLs
    for batch file upload operations to S3 storage.
    """
    filenames: List[str] = Field(
        ..., description="List of filenames for which to generate presigned URLs"
    )


class PresignedFileUrl(BaseModel):
    """
    Model representing a single presigned URL for file upload.
    
    Contains the mapping between a filename, its S3 storage key,
    and the temporary presigned URL for direct upload access.
    """
    filename: str = Field(..., description="Name of the file")
    s3_key: str = Field(..., description="S3 key for the file")
    presigned_url: str = Field(..., description="Presigned URL for file upload")


class GenerateUploadUrlsResponse(BaseModel):
    """
    Response model containing multiple presigned upload URLs.
    
    Returns a list of presigned URLs with their corresponding filenames
    and S3 keys for batch file upload operations.
    """
    urls: List[PresignedFileUrl] = Field(
        ..., description="List of presigned URLs for file uploads"
    )


class TestLabelFilteringRuleRequest(BaseModel):
    """Request model for testing a label filtering rule."""

    image_s3_keys: List[str] = Field(
        ..., description="S3 keys for the images to test against"
    )


class TestLabelFilteringRuleLabel(BaseModel):
    """Model for label detection results."""

    name: str = Field(..., description="Name of the detected label")
    confidence: float = Field(
        ..., description="Confidence score of the label detection"
    )
    s3_key: str = Field(
        ..., description="S3 key of the image where the label was detected"
    )


class TestLabelFilteringRuleResponse(BaseModel):
    """Response model for testing label filtering prompt."""

    labels: List[TestLabelFilteringRuleLabel] = Field(
        ..., description="Labels that were detected in the images"
    )


class TestDescriptionFilterPromptRequest(BaseModel):
    """Request model for testing description filtering prompt."""

    description: str = Field(..., description="Description to test against the item")
    image_s3_keys: List[str] = Field(
        ..., description="S3 keys for the images to test against"
    )
    agent_ids: Optional[List[str]] = Field(
        None, description="Optional list of agent IDs to use for the test"
    )
    search_internet: bool = Field(
        False, description="Whether to search the internet for additional information during the test"
    )


class TestDescriptionFilterPromptResponse(BaseModel):
    """Response model for testing description filtering prompt."""

    response: CallUsingAllFilesResponse = Field(
        ..., description="Response from the description filtering prompt test"
    )


# --- Agent Models ---
class AgentListResponse(BaseModel):
    """Response model for listing agents."""

    agents: List[Agent] = Field(
        ..., description="List of agents"
    )


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent."""

    name: str = Field(..., description="Name of the agent")
    description: Optional[str] = Field(None, description="Optional description of the agent")
    prompt: str = Field(..., description="Prompt for the agent")
    type: str = Field(..., description="Type of the agent (Knowledge Base or REST API)")
    knowledge_base_id: Optional[str] = Field(None, description="ID of the knowledge base to be used by the agent (required for Knowledge Base agents)")
    api_endpoint: Optional[str] = Field(None, description="Endpoint URL of the REST API to be used by the agent (required for REST API agents)")
    athena_database: Optional[str] = Field(..., description="Name of the Amazon Athena database to be used by the agent. Only applicable for Amazon Athena agents.")
    athena_query: Optional[str] = Field(..., description="SQL query to be executed against the Amazon Athena database. Only applicable for Amazon Athena agents.")

class UpdateAgentRequest(BaseModel):
    """Request model for updating an agent."""

    name: Optional[str] = Field(None, description="Name of the agent")
    description: Optional[str] = Field(None, description="Optional description of the agent")
    prompt: Optional[str] = Field(None, description="Prompt for the agent")
    type: Optional[str] = Field(None, description="Type of the agent (Knowledge Base or REST API)")
    knowledge_base_id: Optional[str] = Field(None, description="ID of the knowledge base to be used by the agent")
    api_endpoint: Optional[str] = Field(None, description="Endpoint URL of the REST API to be used by the agent")
    athena_database: Optional[str] = Field(..., description="Name of the Amazon Athena database to be used by the agent. Only applicable for Amazon Athena agents.")
    athena_query: Optional[str] = Field(..., description="SQL query to be executed against the Amazon Athena database. Only applicable for Amazon Athena agents.")