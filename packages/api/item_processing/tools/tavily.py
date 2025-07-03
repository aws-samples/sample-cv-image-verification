
from strands import tool
from tavily import TavilyClient
from strands.types.tools import ToolUse
import boto3

from constants import TAVILY_API_KEY_SECRET

@tool(
    name="tavily_search_tool",
    description="Searches the web for up-to-date information. Only use this tool to find current information about any information that is not available in the knowledge base.",
    inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query to search the Internet for information",
                    }
                },
                "required": ["query"]
            }
)
def tavily_search_tool(query:str) -> str:
    """
    Search the internet for results matching the query string.

    Use this tool when you need to find detailed information from the internet. Only use it when the knowledge base does not have the required information.

    Example response:
        {
            "query": "2007 Pajero Engine Issues",
            "follow_up_questions": null,
            "answer": "The 2007 Mitsubishi Pajero, particularly the 3.2 DiD (Direct injection Diesel) model, experiences several common engine-related issues that frequently cause the vehicle to enter limp mode. The primary problems include faulty suction control valves, malfunctioning MAP (Manifold Absolute Pressure) sensors, and defective throttle control valves, with the suction control valve being a particularly recurring issue. Beyond these specific engine components, the 2007 Pajero also suffers from gearbox noise problems, typically manifesting as a squealing sound around 2200rpm due to poor gearbox integration. These issues are well-documented among owners and represent the most frequently reported problems for this model year, affecting the vehicle's performance and requiring attention to maintain proper operation.",
            "images": [],
            "results": [
                {
                "title": "NS DiD engine issues experienced and fixes - Pajero 4WD Club of ...",
                "url": "https://www.pajeroforum.com.au/forum/vehicles/generation-4-1-pajero/22449-ns-did-engine-issues-experienced-and-fixes",
                "content": "Share Tweet #1 NS DiD engine issues experienced and fixes 14-02-12, 06:57 PM I thought id repost this as a thread if people are interested My Paj ns 2007 3.2 DID auto with Chipit Common problems that causes limp mode etc Suction Control Valve Map sensor Throttle control valve Suction control valve Symptoms",
                "score": 0.6862234,
                "raw_content": null
                },
                {
                "title": "Mitsubishi Pajero 2007 Problems - CarsGuide",
                "url": "https://www.carsguide.com.au/mitsubishi/pajero/problems/2007",
                "content": "Are you having problems with your 2007 Mitsubishi Pajero? Let our team of motoring experts keep you up to date with all of the latest 2007 Mitsubishi Pajero issues & faults. We have gathered all of the most frequently asked questions and problems relating to the 2007 Mitsubishi Pajero in one spot to help you decide if it's a smart buy.",
                "score": 0.6633424,
                "raw_content": null
                },
                {
                "title": "9 Common Mitsubishi Pajero Problems You Should Know!",
                "url": "https://dandenongcarwrecker.com.au/9-common-mitsubishi-pajero-problems-you-should-know/",
                "content": "9. GearBox Noise Besides the rumbling noise from the engine side, the gearbox of Mitsubishi Pajero also causes potential noise at around 2200rpm. It has disturbed many users since it is a squealing noise. The poor integration of the gearbox causes this problem to occur repetitively. Conclusion Purchasing a car can be one of the biggest",
                "score": 0.518815,
                "raw_content": null
                },
                {
                "title": "Mitsubishi Pajero Problems: Common Issues and Owner Feedback",
                "url": "https://enginecrux.com/mitsubishi-pajero-problems-facts-and-owner-insights/",
                "content": "Explore common Mitsubishi Pajero problems, owner feedback, and key facts to keep your vehicle running smoothly.",
                "score": 0.32463187,
                "raw_content": null
                },
                {
                "title": "4 Mitsubishi Pajero Common Problems You Should Be Aware Of!",
                "url": "https://www.driversadvice.com/mitsubishi-pajero-common-problems/",
                "content": "Mitsubishi Pajero has also been known under the names Montero and Shogun, its name change usually comes from the derogatory meaning of the vehicle in certain countries. The car has a front engine with four-wheel drive, which makes Mitsubishi Pajero a potent vehicle that can cross less than optimal terrain easily.",
                "score": 0.29899308,
                "raw_content": null
                }
            ],
            "response_time": 6.17
        }

    Notes:
        - This tool searches the internet using the Tavily API.
        - It returns a structured response with the search results, including titles, URLs, content snippets,
          and relevance scores.
        - For further processing, you can use the `http_request` tool to fetch full content from URLs if needed.

    Args:
        query: The search string (product name, category, or keywords)
               Example: "red running shoes" or "smartphone charger"

    Returns:
        A JSON object containing the search results, including:
        - `query`: The original search query
        - `follow_up_questions`: Any follow-up questions (if applicable)
        - `answer`: A summary answer based on the search results
        - `images`: A list of image URLs related to the search
        - `results`: A list of search results, each with:
            - `title`: The title of the search result
            - `url`: The URL of the search result
            - `content`: A snippet of the content from the search result
            - `score`: The relevance score of the search result
            - `raw_content`: The raw content of the search result (if available)
    Raises:
        - Exception: If there is an error during the search process
    """
    try:
        
        print(f"Received query for Tavily search: {query}")
        if not query:
            return "No query provided for Tavily search"
        
        # Use Secrets manager to get the Tavily API key
        
        tavily_api_key = boto3.client('secretsmanager').get_secret_value(
            SecretId=TAVILY_API_KEY_SECRET
        )["SecretString"]
        
        client = TavilyClient(tavily_api_key)
        response = client.search(
            query=query,
            include_answer="advanced"
        )
        print('Response from Tavily:',response)
    
        return str(response)
    except Exception as e:
        print(f"Error in Tavily search tool: {e}")
        
        return f"Error in Tavily search: {str(e)}"
