from decimal import Decimal
from typing import Dict, Optional, Any, Type
from pydantic import BaseModel, ValidationError


def _parse_decimals(data: Any) -> Any:
    """Recursively converts Decimal instances to int (if whole) or float."""
    if isinstance(data, Decimal):
        return int(data) if data % 1 == 0 else float(data)
    elif isinstance(data, dict):
        return {k: _parse_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_parse_decimals(item) for item in data]
    else:
        return data


def dynamodb_item_to_pydantic(
    item: Dict[str, Any], model_class: Type[BaseModel]
) -> Optional[BaseModel]:
    """Converts a DynamoDB item to a Pydantic model instance."""
    if not item:
        return None

    try:
        item_with_parsed_decimals = _parse_decimals(item)
        return model_class.model_validate(item_with_parsed_decimals)
    except (ValidationError, Exception):
        return None
