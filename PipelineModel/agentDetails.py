from typing import Optional, List
from pydantic import BaseModel

from PipelineModel.AgentTools import AgentTools, AgentUserTools
from PipelineModel.agentLLM import AgentLLM
from PipelineModel.taskDetails import TaskDetails
from PipelineModel.agentEmbedding import AgentEmbedding

class AgentDetails(BaseModel):
    id: int
    name: Optional[str] = None
    role: Optional[str] = None
    goal: Optional[str] = None
    backstory: Optional[str] = None
    verbose: Optional[bool] = None
    allowDelegation: Optional[bool] = None
    maxIter: Optional[int] = 0
    maxRpm: Optional[int] = 0
    maxExecutionTime: Optional[int] = 0
    task: TaskDetails
    llm: AgentLLM
    embedding: Optional[List[AgentEmbedding]] = None
    tools: list[AgentTools] = []
    allowCodeExecution: Optional[bool] = False
    isSafeCodeExecution: Optional[bool] = False
    userTools: Optional[list[AgentUserTools]] = []
