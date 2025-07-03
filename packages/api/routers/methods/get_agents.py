from typing import List
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from schemas.datamodel import Agent
from .agent_utils import agent_table, dynamodb_item_to_agent

async def get_agents() -> List[Agent]:
    """
    Retrieve a list of all Agents.
    
    Returns:
        List[Agent]: A list of all Agent objects.
    """
    try:
        response = agent_table.scan()
        agents = []
        
        for item in response.get("Items", []):
            agent = dynamodb_item_to_agent(item)
            agents.append(agent)
            
        return agents
        
    except ClientError as e:
        print(f"Error retrieving Agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Agents: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error retrieving Agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
