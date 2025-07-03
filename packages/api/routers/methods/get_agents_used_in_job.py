from typing import List, Set
from fastapi import HTTPException, status
from schemas.datamodel import Agent
from .verification_job_utils import fetch_verification_job
from .get_agent import get_agent as get_agent_impl


async def get_agents_used_in_job(verification_job_id: str) -> List[Agent]:
    """
    Retrieve all agents used in a specific verification job.
    
    Args:
        verification_job_id (str): The unique identifier of the verification job.
        
    Returns:
        List[Agent]: A list of Agent objects used in the verification job.
    """
    try:
        # Fetch the verification job
        verification_job, _ = fetch_verification_job(verification_job_id)
        
        # Collect unique agent IDs from all item instances
        agent_ids: Set[str] = set()
        
        for item_instance in verification_job.items:
            if item_instance.agent_ids:
                agent_ids.update(item_instance.agent_ids)
        
        # Fetch all agents by their IDs
        agents: List[Agent] = []
        for agent_id in agent_ids:
            try:
                agent = await get_agent_impl(agent_id)
                agents.append(agent)
            except HTTPException as e:
                # Log the error but continue with other agents
                print(f"Warning: Could not retrieve agent {agent_id}: {e.detail}")
                continue
        
        return agents
        
    except ValueError as e:
        # Re-raise verification job not found errors
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        print(f"Unexpected error retrieving agents for job {verification_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
