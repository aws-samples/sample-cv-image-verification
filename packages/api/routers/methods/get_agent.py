from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from schemas.datamodel import Agent
from .agent_utils import agent_table, dynamodb_item_to_agent


async def get_agent(agent_id: str) -> Agent:
    """
    Retrieve a specific Agent by its ID.
    
    Args:
        agent_id (str): The unique identifier of the Agent to retrieve.
        
    Returns:
        Agent: The Agent object corresponding to the given ID.
    """
    try:
        response = agent_table.get_item(Key={"id": agent_id})
        
        if "Item" not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )
        
        agent = dynamodb_item_to_agent(response["Item"])
        return agent
        
    except HTTPException:
        raise
    except ClientError as e:
        print(f"Error retrieving Agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Agent: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error retrieving Agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
