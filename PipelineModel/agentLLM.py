from pydantic import BaseModel
from typing import Optional

class AgentLLM(BaseModel):
    model: str
    aiEngine: str
    temperature: float
    maxToken: int
    topP: float

    llmDeploymentName: Optional[str] = None
    apiKey: Optional[str] = None
    azureEndpoint: Optional[str] = None
    llmApiVersion: Optional[str] = None
    
    bedrockModelId: Optional[str] = None
    region: Optional[str] = None
    accessKey: Optional[str] = None
    secretKey: Optional[str] = None

    vertexAIEndpoint: Optional[str] = None
    gcpProjectId: Optional[str] = None
    gcpLocation: Optional[str] = None
