from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from schemas.datamodel import Agent, AgentTypes
from schemas.requests_responses import CreateAgentRequest
from .agent_utils import agent_table, agent_to_dynamodb_item
import time
import uuid


async def create_agent(agent_request: CreateAgentRequest) -> Agent:
    """
    Creates a new Agent in the database.

    Args:
        agent_request (CreateAgentRequest): The request containing agent details.

    Returns:
        Agent: The newly created agent.
    """
    
    # Generate unique ID and timestamps
    agent_id = str(uuid.uuid4())
    current_time = int(time.time())
    
    # Convert string type to enum
    agent_type = AgentTypes(agent_request.type)
    
    # Create the Agent object
    agent = Agent(
        id=agent_id,
        created_at=current_time,
        updated_at=current_time,
        name=agent_request.name,
        description=agent_request.description,
        prompt=agent_request.prompt,
        type=agent_type,
        api_endpoint=agent_request.api_endpoint,
        knowledge_base_id=agent_request.knowledge_base_id,
        athena_database=agent_request.athena_database,
        athena_query=agent_request.athena_query if agent_request.athena_query else None,
    )
    
    # Insert the agent into the database
    try:
        item = agent_to_dynamodb_item(agent)
        agent_table.put_item(Item=item)
        
        return agent
        
    except ClientError as e:
        print(f"Error creating Agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error creating Agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
