from pydantic import BaseModel

class Message(BaseModel):
    progress: str
    content:str
    sender:str
    executionId: str
    pipelineId:str
