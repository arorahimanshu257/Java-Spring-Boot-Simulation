from typing import Optional, Dict

from pydantic import BaseModel
from PipelineModel.AgentTools import AgentTools, AgentUserTools

class PipelineRequest(BaseModel):
    pipeLineId: int
    executionId: Optional[str]
    userInputs: Dict[str,str]
    user: str
    tools: list[AgentTools] = []
    userTools: Optional[list[AgentUserTools]] = []
