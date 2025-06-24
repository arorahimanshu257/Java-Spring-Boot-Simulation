from typing import Optional, Dict
from pydantic import BaseModel

from PipelineModel.TasksOutputModel import TasksOutputModel
from PipelineModel.agent import Agent
from PipelineModel.agentEmbedding import AgentEmbedding
from PipelineModel.agentLLM import AgentLLM
from PipelineModel.langfuse import LangFuse


class PipelineModel(BaseModel):
    pipelineId: int
    executionId: Optional[str] = None
    name: Optional[str] = None
    user: Optional[str] = None
    description: Optional[str] = None
    userInputs: Optional[Dict[str,str]] = None
    managerLlm: Optional[AgentLLM] = None
    masterEmbedding: Optional[AgentEmbedding] = None
    pipeLineAgents: list[Agent]
    langfuse: LangFuse
    tasksOutputs: list[TasksOutputModel] = []
    output: Optional[str] = None
    enableAgenticMemory: Optional[bool] = False
    file_download_url: str = None

