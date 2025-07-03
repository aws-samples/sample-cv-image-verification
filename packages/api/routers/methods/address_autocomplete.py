from fastapi import HTTPException, status

# Import the utility function directly
from utils.map import get_address_suggestions
from schemas.requests_responses import AddressAutocompleteResponse


async def address_autocomplete(query: str) -> AddressAutocompleteResponse:
    """
    Implementation to provide address autocomplete suggestions based on user input.
    """
    try:
        suggestions = get_address_suggestions(query)
        return AddressAutocompleteResponse(suggestions=suggestions)
    except Exception as e:
        print(f"Error during address autocomplete implementation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during address autocomplete: {str(e)}",
        ) from e
