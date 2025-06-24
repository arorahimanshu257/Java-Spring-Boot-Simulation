from typing import Optional

from pydantic import BaseModel

class RuntimeLogs(BaseModel):
    pipelineId: int
    progress: str
    content: str
    color: Optional[str] = None
    sender: str
    executionId: str

def to_dict(self):
    return {
        "pipelineId": self.pipelineId,
        "progress": self.progress,
        "content": self.content,
        "color": self.color,
        "sender": self.sender,
        "executionId": self.executionId
    }