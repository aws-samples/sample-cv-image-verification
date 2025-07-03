import time
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from schemas.datamodel import Agent, AgentTypes
from schemas.requests_responses import UpdateAgentRequest
from .agent_utils import agent_table, agent_to_dynamodb_item, dynamodb_item_to_agent


async def update_agent(agent_id: str, agent_request: UpdateAgentRequest) -> Agent:
    """
    Update an existing Agent identified by its ID.
    
    Args:
        agent_id (str): The unique identifier of the Agent to update.
        agent_request (UpdateAgentRequest): The request body containing the updated agent details.
        
    Returns:
        Agent: The updated Agent object.
    """
    try:
        # First, get the existing agent
        response = agent_table.get_item(Key={"id": agent_id})
        
        if "Item" not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )
        
        existing_agent = dynamodb_item_to_agent(response["Item"])
        
        # Update fields if provided
        updated_data = {
            "id": agent_id,
            "created_at": existing_agent.created_at,
            "updated_at": int(time.time()),
            "name": agent_request.name if agent_request.name is not None else existing_agent.name,
            "description": agent_request.description if agent_request.description is not None else existing_agent.description,
            "prompt": agent_request.prompt if agent_request.prompt is not None else existing_agent.prompt,
            "type": AgentTypes(agent_request.type) if agent_request.type is not None else existing_agent.type,
            "api_endpoint": agent_request.api_endpoint if agent_request.api_endpoint is not None else existing_agent.api_endpoint,
            "knowledge_base_id": agent_request.knowledge_base_id if agent_request.knowledge_base_id is not None else existing_agent.knowledge_base_id,
            "athena_database": agent_request.athena_database if agent_request.athena_database is not None else existing_agent.athena_database,
            "athena_query": agent_request.athena_query if agent_request.athena_query is not None else existing_agent.athena_query,
        }
        
        updated_agent = Agent(**updated_data)
        
        # Save the updated agent
        agent_data = agent_to_dynamodb_item(updated_agent)
        agent_table.put_item(Item=agent_data)
        
        return updated_agent
        
    except HTTPException:
        raise
    except ClientError as e:
        print(f"Error updating Agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Agent: {str(e)}",
        ) from e
    except Exception as e:
        print(f"Unexpected error updating Agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
