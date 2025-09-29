from src.gaspipe.validate import validate_frameindex
from src.gaspipe.types import FrameIndex

def test_validate_frameindex_ok():
    data = {"video_id":"v1","frame_count":2,"fps":30.0,"resolution":[1920,960],"files":["a.png","b.png"]}
    obj = validate_frameindex(data)
    assert isinstance(obj, FrameIndex)
