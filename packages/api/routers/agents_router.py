from typing import List
from fastapi import APIRouter, HTTPException, status
from schemas.datamodel import Agent
from schemas.requests_responses import (
    AgentListResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
)

# Import the implementation functions from the method files
from .methods.get_agents import get_agents as get_agents_impl
from .methods.get_agent import get_agent as get_agent_impl
from .methods.create_agent import create_agent as create_agent_impl
from .methods.update_agent import update_agent as update_agent_impl
from .methods.delete_agent import delete_agent as delete_agent_impl
from .methods.get_agents_used_in_job import get_agents_used_in_job as get_agents_used_in_job_impl

# Main router for Agent operations
router = APIRouter()


# Define routes directly, calling the imported implementation functions
@router.get("/", response_model=AgentListResponse)
async def get_agents() -> AgentListResponse:
    """
    Retrieves a list of all Agents.

    Returns:
        AgentListResponse: A response object containing a list of Agents.
    """
    agents = await get_agents_impl()
    return AgentListResponse(agents=agents)

@router.get("/job/{verification_job_id}", response_model=AgentListResponse)
async def get_agents_used_in_job(verification_job_id: str) -> AgentListResponse:
    """
    Retrieves a list of all agents used in a specific verification job.

    Args:
        verification_job_id (str): The unique identifier of the verification job.

    Returns:
        AgentListResponse: A response object containing a list of agents used in the job.
    """
    agents = await get_agents_used_in_job_impl(verification_job_id)
    return AgentListResponse(agents=agents)


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> Agent:
    """
    Retrieves a specific Agent by its ID.

    Args:
        agent_id (str): The unique identifier of the Agent to retrieve.

    Returns:
        Agent: The Agent object corresponding to the given ID.
    """
    return await get_agent_impl(agent_id)


@router.post("/", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_request: CreateAgentRequest) -> Agent:
    """
    Creates a new Agent based on the provided request data.

    Args:
        agent_request (CreateAgentRequest): The request body containing the details for the new Agent.

    Returns:
        Agent: The newly created Agent object.
    """
    return await create_agent_impl(agent_request)


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_request: UpdateAgentRequest) -> Agent:
    """
    Updates an existing Agent identified by its ID with the provided data.

    Args:
        agent_id (str): The unique identifier of the Agent to update.
        agent_request (UpdateAgentRequest): The request body containing the updated Agent details.

    Returns:
        Agent: The updated Agent object.
    """
    return await update_agent_impl(agent_id, agent_request)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str) -> None:
    """
    Deletes an Agent identified by its ID.

    Args:
        agent_id (str): The unique identifier of the Agent to delete.

    Returns:
        None: Returns None with a 204 No Content status code upon successful deletion.
    """
    await delete_agent_impl(agent_id)
    return None  # Explicitly return None for 204
