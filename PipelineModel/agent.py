from pydantic import BaseModel
from PipelineModel.agentDetails import AgentDetails

class Agent(BaseModel):
    serial: int
    agent: AgentDetails

