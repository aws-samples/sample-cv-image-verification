from fastapi import HTTPException, status
from botocore.exceptions import ClientError

# Import the utility function directly
from utils.map import get_coordinates_from_address

# Define request/response models locally or import if defined elsewhere
from pydantic import BaseModel


class CoordinatesRequest(BaseModel):
    address: str


class CoordinatesResponse(BaseModel):
    latitude: float
    longitude: float


async def get_coordinates(request: CoordinatesRequest) -> CoordinatesResponse:
    """
    Implementation to get the latitude and longitude coordinates for a given address.
    """
    try:
        coordinates = get_coordinates_from_address(request.address)
        if coordinates is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find coordinates for the address: {request.address}",
            )
        latitude, longitude = coordinates
        return CoordinatesResponse(latitude=latitude, longitude=longitude)
    except ClientError as e:
        print(f"Error calling AWS Location Service for coordinates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get coordinates: {e.response['Error']['Message']}",
        ) from e
    except HTTPException as e:  # Re-raise our 404
        raise e
    except Exception as e:
        print(f"Unexpected error getting coordinates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
