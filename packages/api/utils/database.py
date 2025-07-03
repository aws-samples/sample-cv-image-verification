import json
from decimal import Decimal
from pydantic import BaseModel


# Helper function to convert Pydantic models to DynamoDB format
# Handles Decimal conversion for numbers and removes None values
def model_to_dynamodb_item(model: BaseModel):
    # Use model_dump_json for better handling of types like datetime, then parse with Decimal
    item_json = model.model_dump_json(exclude_none=True)
    return json.loads(item_json, parse_float=Decimal)
