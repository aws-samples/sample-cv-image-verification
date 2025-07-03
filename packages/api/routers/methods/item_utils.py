import boto3
from routers.methods.collection_utils import dynamodb_item_to_item
from schemas.datamodel import Item
from constants import AWS_REGION, ITEMS_TABLE_NAME, VERIFICATION_JOBS_TABLE_NAME

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
item_table = dynamodb.Table(ITEMS_TABLE_NAME)
verification_job_table = dynamodb.Table(VERIFICATION_JOBS_TABLE_NAME)


def get_items_by_name(item_name: str) -> list[Item] | None:
    """
    Retrieve an Item by its name attribute.

    Args:
        item_name (str): The name of the Item to retrieve

    Returns:
        list[Item] | None: The retrieved Item objects or None if not found
    """
    from boto3.dynamodb.conditions import Attr

    # Use scan with filter expression to find items by name
    response = item_table.scan(FilterExpression=Attr("name").eq(item_name))

    items = response.get("Items", [])

    # Convert all matching items to Item objects
    item_objects = []
    for item in items:
        item_objects.append(dynamodb_item_to_item(item))
    return item_objects
