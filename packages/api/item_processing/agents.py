
import logging
import os
from typing import Optional
import requests
from strands import Agent, models, tool, tools
from strands.tools import PythonAgentTool
from strands.tools.tools import FunctionTool
from strands.types.tools import ToolUse, ToolResult, ToolSpec
from strands_tools import http_request

import boto3
from item_processing.tools.tavily import tavily_search_tool
from item_processing.tools.rest_api import rest_api_client_tool
from item_processing.tools.athena import athena_query_tool
from schemas.datamodel import AgentTypes
from routers.methods.get_agent import get_agent

logging.getLogger("strands").setLevel(logging.WARNING)

# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)


def knowledge_base_agent_tool(tool_use: ToolUse, *args, **kwargs) -> ToolResult:
    """Callback function for knowledge base agent tool.
    
    Args:
        tool_use: The tool use request containing input parameters
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
        
    Returns:
        ToolResult with the agent response
    """
   
    try:
        # Extract the query from tool input
        tool_input = tool_use.get("input", {})
        query = tool_input.get("query", "")
       
        if not query:
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": "No query provided for knowledge base search"}]
            }
        
        knowledge_base_id = tool_input.get("knowledge_base_id", "")
        if not knowledge_base_id:
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": "No knowledge base ID configured for this agent"}]
            }
        else:
            print(f"Using knowledge base ID: {knowledge_base_id} for query: '{query}'")
        
        # Use Bedrock Agent Runtime to query the knowledge base
        bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")
        
        # Retrieve relevant documents from the knowledge base
        retrieve_response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5,  # Retrieve top 5 most relevant results
                    'overrideSearchType': 'HYBRID'  # Use both semantic and keyword search
                }
            }
        )
        
        
        # Extract and format the retrieved results
        retrieval_results = retrieve_response.get('retrievalResults', [])
        
        print(f"Retrieved {len(retrieval_results)} results for query: '{query}'")
        
        if not retrieval_results:
            response = f"No relevant information found in the knowledge base for query: '{query}'"
        else:
            # Combine the retrieved content
            response_parts = []
            response_parts.append(f"Found {len(retrieval_results)} relevant result(s) for query: '{query}'\n")
            
            for i, result in enumerate(retrieval_results, 1):
                content = result.get('content', {}).get('text', '')
                score = result.get('score', 0)
                metadata = result.get('metadata', {})
                
                response_parts.append(f"\n--- Result {i} (Relevance Score: {score:.3f}) ---")
                
                # Add source information if available
                source_uri = metadata.get('sourceUri', '')
                if source_uri:
                    response_parts.append(f"Source: {source_uri}")
                
                # Add the content
                response_parts.append(f"Content: {content}")
            
            response = "\n".join(response_parts)
            
            print(f"Knowledge base agent response: {response}")
        
        return {
            "toolUseId": tool_use.get("toolUseId", "unknown"),
            "status": "success",
            "content": [{"text": response}]
        }
    except Exception as e:
        print(f"Error in knowledge base agent tool: {e}")
        return {
            "toolUseId": tool_use.get("toolUseId", "unknown"),
            "status": "error",
            "content": [{"text": f"Error in knowledge base agent: {str(e)}"}]
        }

def get_system_prompt() -> str:
    return '''You are an expert in rewriting image verification requirements. You will be provided an image verification description. 
Using the tools available, you will rewrite the item requirements to include all necessary details for image verification, including specific technical details and visually distinguishing features. 
For any URLs returned from tavily_search_tool, use the http_request tool to fetch the content and extract relevant information.
If the item description is already sufficient, return it unchanged.
The image verification description will be used to verify images using a multimodal Claude Sonnet model
Just return the rewritten description without any additional text or explanations.'''

async def augment_item_description(item_description: str,search_internet:bool=False, agent_ids: list[str] = []) -> str:
    """
    Augments an item description by leveraging one or more agents to enrich the content.
    This function takes an item description and enhances it using specialized agents,
    such as knowledge base agents or REST API agents. Each agent contributes additional
    context or information to the original description.
    Args:
        item_description (str): The original item description to be augmented.
        search_internet (bool, optional): Flag to enable internet search during augmentation.
            Defaults to False.
        agent_ids (list[str], optional): List of agent IDs to use for augmentation.
            Defaults to an empty list.
    Returns:
        str: The augmented item description, or the original description if augmentation
             fails or no valid agents are provided.
    Notes:
        - The function uses Claude 3.5 Sonnet model for processing through AWS Bedrock.
        - If no agent IDs are provided, returns the original description unchanged.
        - Currently supports knowledge base agents and has placeholder for REST API agents.
        - Automatically adds HTTP request and Tavily search tools to the agent's toolset.
        - If any error occurs during augmentation, the original description is returned.
    """
    
    model = models.BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-west-2"
    )
    
    if not agent_ids or len(agent_ids) == 0:
        print("No agents provided for augmentation, returning original item description.")
        return item_description
    
    tools_list = []
    
    for agent_id in agent_ids:
        agent = await get_agent(agent_id)
        
        if not agent:
            print(f"Agent with ID {agent_id} not found, skipping.")
            continue
        
        
        if agent.type == AgentTypes.KNOWLEDGE_BASE:
            if not agent.knowledge_base_id:
                print(f"Agent {agent_id} is a knowledge base agent but has no knowledge base ID configured, skipping.")
                continue
            schema = {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to search the knowledge base"
                    },
                    "knowledge_base_id" : {
                        "type": "string",
                        "description": "Knowledge base ID to search",
                        "default": agent.knowledge_base_id
                    }
                },
                "required": ["query","knowledge_base_id"]
            }
            
            kb_tool = PythonAgentTool(
                tool_name=f"knowledge_base_agent_tool",
                tool_spec=ToolSpec(
                    name="knowledge_base_agent_tool",
                    description=str(agent.description),
                    inputSchema=schema
                ),
                callback=lambda tool_use, *args, **kwargs: knowledge_base_agent_tool(
                    tool_use, *args, **kwargs
                )
            )
            
            tools_list.append(kb_tool)
            
        elif agent.type == AgentTypes.REST_API:
            if not agent.api_endpoint:
                print(f"Agent {agent_id} is a REST API agent but has no API endpoint configured, skipping.")
                continue
            
            schema = {
                "type": "object",
                "properties": {
                    "api_endpoint": {
                        "type": "string",
                        "description": "The endpoint to perform a HTTP GET on.",
                        "default": agent.api_endpoint
                    }
                },
                "required": ["api_endpoint"]
            }
            
            rest_api_tool = PythonAgentTool(
                tool_name=f"rest_api_client_tool",
                tool_spec=ToolSpec(
                    name="rest_api_client_tool",
                    description=str(agent.description),
                    inputSchema=schema
                ),
                callback=lambda tool_use, *args, **kwargs: rest_api_client_tool(
                    tool_use, *args, **kwargs
                )
            )
            
            tools_list.append(rest_api_tool)
        elif agent.type == AgentTypes.AMAZON_ATHENA:
            if not agent.athena_database or not agent.athena_query:
                print(f"Agent {agent_id} is an Amazon Athena agent but has no database or query configured, skipping.")
                continue
            
            schema = {
                "type": "object",
                "properties": {
                    "athena_database": {
                        "type": "string",
                        "description": "The Athena database to query.",
                        "default": agent.athena_database
                    },
                     "athena_query": {
                        "type": "string",
                        "description": "The Athena query to execute.",
                        "default": agent.athena_query
                    }
                },
                "required": ["athena_query","athena_database"]
            }
            
            athena_client_tool = PythonAgentTool(
                tool_name=f"athena_query_tool",
                tool_spec=ToolSpec(
                    name="athena_query_tool",
                    description=str(agent.description),
                    inputSchema=schema
                ),
                callback=lambda tool_use, *args, **kwargs: athena_query_tool(
                    tool_use, *args, **kwargs
                )
            )
            
            tools_list.append(athena_client_tool)
        else:
            print(f"Agent {agent_id} is of unknown type, skipping.")
    
    if not tools_list:
        return item_description
    
    if search_internet:
        tools_list.append(http_request)
        tools_list.append(tavily_search_tool)
    
    # Create the agent with tools
    agent = Agent(
        model=model,
        tools=tools_list
    )
    
    # Run the agent to augment the item description
    try:
        response =  agent(f'''{get_system_prompt()}
                          
                          Item Description: {item_description}''')
        return f'Augmented description: {str(response)}'
    except Exception as e:
        # If augmentation fails, return original description
        print(f"Error augmenting item description: {e}")
        return item_description
