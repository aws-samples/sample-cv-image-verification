import boto3
from typing import List, Optional
from botocore.exceptions import ClientError
from schemas.datamodel import AddressSuggestion
from constants import AWS_REGION, LOCATION_INDEX_NAME

client = boto3.client("location", region_name=AWS_REGION)


def get_coordinates_from_address(address):
    """Returns the latitude and longitude of a given address using Amazon Location Services."""
    response = client.search_place_index_for_text(
        IndexName=LOCATION_INDEX_NAME,
        Text=address,
        MaxResults=1,
    )

    if not response.get("Results"):
        return None

    place = response["Results"][0].get("Place")
    if not place or "Geometry" not in place or "Point" not in place["Geometry"]:
        return None

    coordinates = place["Geometry"]["Point"]
    return coordinates[1], coordinates[0]


def address_lookup(lat: float, lon: float) -> Optional[str]:
    """Converts coordinates to an address using reverse geocoding."""
    lat = float(lat)
    lon = float(lon)

    lon = max(min(lon, 180), -180)
    lat = max(min(lat, 90), -90)

    response = client.search_place_index_for_position(
        IndexName=LOCATION_INDEX_NAME,
        Position=[lon, lat],
    )

    if not response.get("Results"):
        return None

    place = response["Results"][0].get("Place")
    if not place or "Label" not in place:
        return None

    return str(place["Label"])


def get_address_suggestions(
    query_text: str, max_results: int = 5
) -> List[AddressSuggestion]:
    """Returns a list of address suggestions based on input text."""
    if not query_text:
        return []

    try:
        response = client.search_place_index_for_text(
            IndexName=LOCATION_INDEX_NAME,
            Text=query_text,
            MaxResults=max_results,
        )

        suggestions = []
        for result in response.get("Results", []):
            place = result.get("Place")
            if place and "Label" in place:
                suggestions.append(
                    AddressSuggestion(
                        text=place["Label"],
                        place_id=place.get("PlaceId"),
                    )
                )
        return suggestions

    except (ClientError, Exception):
        return []


def calculate_distance_between_coordinates(coord1, coord2):
    """Calculate the distance between two sets of coordinates using Haversine formula."""
    from math import radians, sin, cos, sqrt, atan2

    lat1, lon1 = map(radians, coord1)
    lat2, lon2 = map(radians, coord2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    r = 6371.0
    distance = r * c

    return distance
