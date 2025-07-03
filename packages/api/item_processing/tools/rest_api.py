


import requests
from strands.types.tools import ToolUse
from strands.types.tools import ToolUse, ToolResult
import boto3

def rest_api_client_tool(tool_use: ToolUse, *args, **kwargs) -> ToolResult:
    """Callback function for REST API client tool.
    
    Args:
        tool_use: The tool use request containing input parameters
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments
        
    Returns:
        ToolResult with the API response
    """
    try:
        # Extract the API endpoint and parameters from tool input
        tool_input = tool_use.get("input", {})
        api_endpoint = tool_input.get("api_endpoint", "")
        params = tool_input.get("params", {})
        
        if not api_endpoint:
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": "No API endpoint provided"}]
            }
        
        print(f"Using REST API endpoint: {api_endpoint} with params: {params}")
        
        try:
            http_response = requests.get(url=api_endpoint,timeout=10)
            print(f"REST API client response: {http_response.status_code} {http_response.reason}")
            http_response.raise_for_status()  # Raise an error for bad responses
            http_response.close()
            string_response = '''Reponse from {api_endpoint}: 
        {http_response.text}'''

            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "success",
                "content": [{"text": string_response}]
            }
        except requests.RequestException as e:
            print(f"Error making HTTP request to {api_endpoint}: {e}")
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": f"HTTP request error: {str(e)}"}]
            }
        
    except Exception as e:
        print(f"Error in REST API client tool: {e}")
        return {
            "toolUseId": tool_use.get("toolUseId", "unknown"),
            "status": "error",
            "content": [{"text": f"Error in REST API client: {str(e)}"}]
        }