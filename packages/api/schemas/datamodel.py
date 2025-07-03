from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from abc import ABC, abstractmethod

class AgentTypes(Enum):
    """
    Enumeration of different agent types.
    
    This enum defines the various types of agents that can be created,
    such as Knowledge Base Agents and REST API Agents.
    """
    KNOWLEDGE_BASE = "Knowledge Base"
    REST_API = "REST API"
    AMAZON_ATHENA = "Amazon Athena"
    UNKNOWN = "Unknown"

class Agent(BaseModel):
    """
    Agent class for representing an agent that assists with item description modification.
    This model defines the structure for agents that can be of different types such as 
    REST API agents or knowledge base agents. Each agent has a unique identifier, 
    metadata about creation and updates, descriptive information, and type-specific
    configuration parameters.
    Attributes:
        id (str): Unique identifier for the agent.
        created_at (int): Unix timestamp indicating when the agent was created.
        updated_at (int): Unix timestamp indicating when the agent was last updated.
        name (str): Name of the agent.
        description (Optional[str]): Optional description of the agent.
        prompt (str): Prompt template or instructions for the agent.
        type (AgentTypes): Type of the agent (e.g., REST API, knowledge base).
        api_endpoint (Optional[str]): Endpoint URL for REST API agents.
        knowledge_base_id (Optional[str]): ID of the knowledge base for KB agents.
    """
    
    id:str=Field(..., description="Unique identifier for the agent")
    created_at:int=Field(..., description="Timestamp when the agent was created")
    updated_at:int=Field(..., description="Timestamp when the agent was last updated")
    name:str=Field(..., description="Name of the agent")
    description:Optional[str]=Field(None, description="Optional description of the agent")
    prompt:str=Field(..., description="Prompt for the agent")
    type:AgentTypes=Field(..., description="Type of the agent",)
    
    api_endpoint: Optional[str] = Field(..., description="Endpoint URL of the REST API to be used by the agent. Only applicable for REST API agents.")
    knowledge_base_id: Optional[str] = Field(..., description="ID of the knowledge base to be used by the agent. Only applicable for knowledge base agents.")
    athena_database: Optional[str] = Field(..., description="Name of the Amazon Athena database to be used by the agent. Only applicable for Amazon Athena agents.")
    athena_query: Optional[str] = Field(..., description="SQL query to be executed against the Amazon Athena database. Only applicable for Amazon Athena agents.")
    
class DescriptionFilteringRule(BaseModel):
    """
    Represents a rule for filtering items based on text description criteria.
    
    This model defines rules that evaluate text descriptions against specific criteria
    using confidence thresholds to determine relevance.
    """
    id: str
    created_at: int
    updated_at: int
    description: str
    min_confidence: float
    mandatory: bool = False
    
class AugmentedDescriptionFilteringRule(DescriptionFilteringRule):
    augmented_description:Optional[str] = Field(default=None,description="The new description of the rule after being augmented by agents.")

class LabelFilteringRule(BaseModel):
    """
    Represents a rule for filtering items based on image label detection criteria.
    
    This model defines rules that evaluate images based on detected labels,
    confidence scores, and minimum size requirements for the detected objects.
    """
    id: str=Field(..., description="Unique identifier for the label filtering rule")
    created_at: int=Field(..., description="Timestamp when the rule was created")
    updated_at: int
    image_labels: List[str] = []
    min_confidence: float
    min_image_size_percent: float= Field(
        0.0, description="Minimum size percentage of the image that must be occupied by the detected object")

class Item(BaseModel):
    """
    Represents a core item entity that can be verified against collections.
    
    Items define the criteria and rules used to assess whether files in a collection
    meet specific requirements. They contain both label-based and description-based
    filtering rules for comprehensive evaluation.
    """
    
    id: str
    created_at: int
    updated_at: int
    name: str
    description: str
    label_filtering_rules: List[LabelFilteringRule] = []
    description_filtering_rules: List[DescriptionFilteringRule] = []
    cluster_number: Optional[int] = None
    agent_ids: list[str] = Field(default_factory=list, description="List of agent IDs that should be used for this item. Agents will process the item against the collection files and return results based on their specific logic.")

class AssessmentStatus(Enum):
    """
    Enumeration of possible assessment statuses for items, collections, and verification jobs.
    
    Represents the current state of evaluation for various entities in the system,
    tracking progress from initial submission through final approval or rejection.
    """

    PENDING = "Pending"
    ASSESSING = "Assessing"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    NEEDS_REVIEW = "Needs Review"
    ERROR = "Error"


class CollectionFileStatus(Enum):
    """
    Enumeration of possible statuses for individual files within a collection.
    
    Tracks the evaluation state of each file as it's processed against item criteria,
    indicating whether the file is relevant, should be ignored, or requires manual review.
    """
    PENDING = "Pending"
    ASSESSING = "Assessing"
    RELEVANT = "Relevant"
    IGNORED = "Ignored"
    NEEDS_REVIEW = "Needs Review"
    ERROR = "Error"


class CollectionFileItemInstance(BaseModel):
    """
    Represents the assessment result of a collection file against a specific item instance.
    
    This model tracks how a particular file performs against item criteria, including
    status, reasoning, address matching, and associated costs from AI processing.
    """
    
    status: Optional[CollectionFileStatus] = None
    status_reasoning: Optional[str] = None
    item_instance_id: str
    address_match: Optional[bool] = None
    detected_address: Optional[str] = None
    cost: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cluster_number: Optional[int] = Field(None, description="Optional cluster identifier this rule belongs to. For a cluster to be marked as compliant, all rules in it must be satisfied. At least one cluster must be satisfied for the item to be compliant. If no rules are in a cluster, all must be satisfied.")

class CollectionFile(BaseModel):
    """
    Represents a file within a collection that needs to be assessed.
    
    Contains metadata about uploaded files including S3 storage information,
    content type, and optional descriptive information.
    """
    
    id: str
    created_at: int
    s3_key: str
    description: Optional[str] = None
    content_type: str
    filename: str
    size: Optional[int] = None


class CollectionFileInstance(CollectionFile):
    """
    Extended file model that includes assessment results against multiple item instances.
    
    Inherits from CollectionFile and adds tracking of how the file performs
    against various item criteria through file_checks.
    """
    file_checks: List[CollectionFileItemInstance] = []


class ItemInstance(BaseModel):
    """
    Represents an instance of an item being verified against a specific collection.
    
    This model tracks the application of filtering rules to files and maintains
    the assessment results, confidence scores, and approval status for the verification process.
    """

    id: str
    created_at: int
    updated_at: int
    name: str
    description: str
    label_filtering_rules_applied: List[LabelFilteringRule]
    description_filtering_rules_applied: List[DescriptionFilteringRule]
    assessment_reasoning: Optional[str] = None
    status: AssessmentStatus = AssessmentStatus.PENDING
    approved_files: List[CollectionFileInstance] = []
    address: Optional[str] = None
    confidence: Optional[float] = None
    item_id: str
    results_log: Optional[str] = None
    cluster_number: Optional[int] = None
    agent_ids: List[str] = Field(default_factory=list, description="List of agent IDs that should be used for this item. Agents will process the item against the collection files and return results based on their specific logic.")


class VerificationJob(BaseModel):
    """
    Represents a verification job that processes a collection against multiple items.
    
    This model orchestrates the verification process, tracking overall status,
    aggregated results, and associated costs while processing items and files.
    """
    
    id: str
    created_at: int
    updated_at: int
    collection_id: str
    status: AssessmentStatus = AssessmentStatus.PENDING
    confidence: Optional[float] = None
    aggregated_results: Optional[str] = None
    items: List[ItemInstance] = []
    files: List[CollectionFileInstance] = []
    error_message: Optional[str] = None
    cost: Optional[float] = None
    search_internet: Optional[bool] = Field(
        False,
        description="Flag indicating whether to search the internet for additional information during verification. Defaults to False.")


class VerificationJobDto(VerificationJob):
    """
    Data Transfer Object for verification jobs with additional display information.
    
    Extends VerificationJob with additional fields for UI presentation,
    including collection name and total cost calculations.
    """
    collection_name: Optional[str] = None
    total_cost: Optional[float] = None


class VerificationJobLogEntry(BaseModel):
    """
    Represents a log entry for verification job execution tracking.
    
    Stores timestamped log messages with severity levels to track
    the progress and issues during verification job processing.
    """
    id: str
    timestamp: int
    verification_job_id: str
    level: str
    message: str


class Collection(BaseModel):
    """
    Represents a collection of files to be verified against items.
    
    Collections serve as the primary container for files that need assessment,
    including optional address information and associated items for verification.
    """
    

    id: str
    created_at: int
    updated_at: int
    description: Optional[str] = None
    files: List[CollectionFile] = []
    address: Optional[str] = None
    items: List[Item] = []


class AddressSuggestion(BaseModel):
    """Represents a single address suggestion."""

    text: str = Field(..., description="The full suggested address text")
    place_id: Optional[str] = Field(
        None,
        description="Optional unique identifier for the place from the location service",
    )
