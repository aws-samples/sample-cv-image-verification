import boto3
from typing import List, Dict, Any
from constants import AWS_REGION, AGENTS_TABLE_NAME
from schemas.datamodel import Agent, AgentTypes
from .collection_utils import model_to_dynamodb_item

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
agent_table = dynamodb.Table(AGENTS_TABLE_NAME)


def dynamodb_item_to_agent(item: Dict[str, Any]) -> Agent:
    """
    Convert a DynamoDB item to an Agent object.
    
    Args:
        item: DynamoDB item dictionary
        
    Returns:
        Agent: Agent object
    """
    agent_type_str = item.get("type", "")
    agent_type = AgentTypes(agent_type_str)
    
    return Agent(
        id=item["id"],
        created_at=int(item["created_at"]),
        updated_at=int(item["updated_at"]),
        name=item["name"],
        description=item.get("description"),
        prompt=item["prompt"],
        type=agent_type,
        api_endpoint=item.get("api_endpoint"),
        knowledge_base_id=item.get("knowledge_base_id"),
        athena_database=item.get("athena_database"),
        athena_query=item.get("athena_query", None),
    )


def agent_to_dynamodb_item(agent: Agent) -> Dict[str, Any]:
    """
    Convert an Agent object to a DynamoDB item.
    
    Args:
        agent: Agent object to convert
        
    Returns:
        Dict[str, Any]: DynamoDB item dictionary
    """
    return model_to_dynamodb_item(agent)


def get_agents_by_name(agent_name: str) -> List[Agent]:
    """
    Retrieve agents by their name attribute.

    Args:
        agent_name (str): The name of the agents to retrieve

    Returns:
        List[Agent]: List of retrieved agent objects
    """
    from boto3.dynamodb.conditions import Attr

    # Use scan with filter expression to find agents by name
    response = agent_table.scan(FilterExpression=Attr("name").eq(agent_name))

    items = response.get("Items", [])

    # Convert all matching items to Agent objects
    agent_objects = []
    for item in items:
        agent_objects.append(dynamodb_item_to_agent(item))
    return agent_objects
