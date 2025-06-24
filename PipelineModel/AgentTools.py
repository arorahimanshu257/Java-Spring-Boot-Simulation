from pydantic import BaseModel
from PipelineModel.AgentToolParams import AgentToolParams

class AgentTools(BaseModel):
    toolId: int
    toolName: str
    parameters: list[AgentToolParams] = []

class AgentUserTools(BaseModel):
    toolId: int
    toolName: str
    toolClassName: str
    toolClassDef: str