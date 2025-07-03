from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from .agent_utils import agent_table


async def delete_agent(agent_id: str) -> None:
    """
    Delete an Agent identified by its ID.
    
    Args:
        agent_id (str): The unique identifier of the Agent to delete.
        
    Returns:
        None: Returns None with a 204 No Content status code upon successful deletion.
    """
    try:
        # First, check if the agent exists
        response = agent_table.get_item(Key={"id": agent_id})
        
        if "Item" not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )
        
        # Delete the agent
        agent_table.delete_item(Key={"id": agent_id})
        
    except HTTPException:
        raise
    except ClientError as e:
        print(f"Error deleting Agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Agent: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error deleting Agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
