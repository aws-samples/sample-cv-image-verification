


import pandas as pd
import requests
from strands.types.tools import ToolUse
from strands.types.tools import ToolUse, ToolResult
import boto3
from time import sleep

from constants import STORAGE_BUCKET_NAME

def format_df_for_llm(df, max_rows=100):
    """
    Format a pandas DataFrame into a string representation optimized for Large Language Models.
    This function prepares DataFrame data for consumption by LLMs by:
    1. Resetting the index if it contains meaningful information
    2. Limiting the number of rows to avoid token overflow
    3. Rounding floating point values for cleaner display
    4. Adding summary metadata about the DataFrame
    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to format for LLM consumption
    max_rows : int, default=100
        Maximum number of rows to include in the output. If the DataFrame has more rows,
        only the first and last max_rows/2 will be included with a note about omitted rows.
    Returns
    -------
    str
        A formatted string representation of the DataFrame containing summary information
        and the data in a readable format.
    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    >>> print(format_df_for_llm(df))
    Results Summary:
    Dimensions: 3 rows × 2 columns
    Columns: A, B
    Data:
       A  B
    0  1  4
    1  2  5
    2  3  6
    """
    # Reset index if it contains meaningful information
    if df.index.name or not all(df.index == range(len(df))):
        df = df.reset_index()
    
    # Handle large DataFrames
    if len(df) > max_rows:
        head = df.head(max_rows//2)
        tail = df.tail(max_rows//2)
        df = pd.concat([head, tail])
        middle_info = f"\n... ({len(df) - max_rows} rows omitted) ...\n"
    else:
        middle_info = ""
    
    # Format floating point numbers
    df = df.round(2)  # Round floating point numbers to 2 decimal places
    
    # Convert to string with clean formatting
    df_string = (
        "Results Summary:\n"
        f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns\n"
        f"Columns: {', '.join(df.columns)}\n\n"
        f"Data:\n{df.to_string()}\n"
        f"{middle_info}"
    )
    
    return df_string

def athena_query_tool(tool_use: ToolUse, *args, **kwargs) -> ToolResult:
    """
    Execute a query against Amazon Athena and return the results.
    This function takes query parameters, executes the query against the specified
    Athena database, and returns the results in a formatted structure. It handles
    the complete workflow of submitting the query, waiting for completion, and
    processing the results.
    Args:
        tool_use (ToolUse): A dictionary-like object containing:
            - input (dict): Contains query parameters:
                - athena_database (str): Name of the Athena database to query
                - athena_query (str): SQL query to execute against the database
            - toolUseId (str): Unique identifier for this tool invocation
        *args: Variable length argument list (not used)
        **kwargs: Arbitrary keyword arguments (not used)
    Returns:
        ToolResult: A dictionary with the following structure:
            - toolUseId (str): The identifier passed in the request
            - status (str): Either "success" or "error"
            - content (list): A list containing a dictionary with the response text:
                - For success: Formatted query results as text
                - For error: Error message
    Raises:
        No exceptions are raised as they're caught internally and returned as error responses.
    Notes:
        - Results are stored in S3 at s3://{STORAGE_BUCKET_NAME}/athena-results/{toolUseId}/
        - The function polls until the query completes or fails
        - Results are converted to a pandas DataFrame and formatted using format_df_for_llm()
    """
    
    try:
        # Extract the API endpoint and parameters from tool input
        tool_input = tool_use.get("input", {})
        athena_database = tool_input.get("athena_database", "")
        athena_query = tool_input.get("athena_query", "")
        toolUseId = tool_use.get("toolUseId", "unknown")
        
        athena_client = boto3.client('athena')
        
        if not athena_database:
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": "No Athena database provided"}]
            }
            
        if not athena_query:
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": "No Athena query provided"}]
            }
        
        print(f"Querying Athena database: {athena_database} with query: {athena_query}")
        
        try:
            response = athena_client.start_query_execution(
            QueryString=athena_query,
            QueryExecutionContext={
                'Database': athena_database  # Replace with your database name
            },
            ResultConfiguration={
                'OutputLocation': f's3://{STORAGE_BUCKET_NAME}/athena-results/{toolUseId}/' 
                }
            )
    
            query_execution_id = response['QueryExecutionId']
        
            # Wait for query to complete
            while True:
                response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
                state = response['QueryExecution']['Status']['State']
                
                if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                sleep(1)
            
                # Get results if query succeeded
                if state == 'SUCCEEDED':
                    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
                    
                    # Convert to pandas DataFrame for easier handling
                    columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
                    data = []
                    for row in results['ResultSet']['Rows'][1:]:  # Skip header row
                        data.append([field.get('VarCharValue', '') for field in row['Data']])
                    
                    df = pd.DataFrame(data, columns=columns)
                    return {
                        "toolUseId": toolUseId,
                        "status": "success",
                        "content": [{"text": format_df_for_llm(df)}]
                    }
                else:
                    print(f"Query failed with state: {state}")
                    return {
                    "toolUseId": tool_use.get("toolUseId", "unknown"),
                    "status": "error",
                    "content": [{"text": f"Query failed with state: {state}"}]
                    }

        except Exception as e:
            print(f"Query failed with exception: {e}")
            return {
                "toolUseId": tool_use.get("toolUseId", "unknown"),
                "status": "error",
                "content": [{"text": f"Query failed with exception: {e}"}]
            }
    except Exception as e:
        print(f"Query failed with exception: {e}")
        return {
            "toolUseId": tool_use.get("toolUseId", "unknown"),
            "status": "error",
            "content": [{"text": f"Query failed with exception: {e}"}]
        }