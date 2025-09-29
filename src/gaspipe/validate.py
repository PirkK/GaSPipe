import json
from pydantic import ValidationError
from .types import FrameIndex

def validate_frameindex(data):
    try:
        return FrameIndex.parse_obj(data)
    except ValidationError as e:
        raise ValueError(json.dumps({"code":"VALIDATION_ERROR","message":"FrameIndex invalid","details":e.errors()}))
