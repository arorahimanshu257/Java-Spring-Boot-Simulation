from typing import Optional

from pydantic import BaseModel

class AgentToolParams(BaseModel):
    id: int
    parameterName: str
    parameterType: str
    value: Optional[str] = None
