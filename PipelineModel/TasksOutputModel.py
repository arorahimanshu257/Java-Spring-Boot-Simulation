from pydantic import BaseModel

class TasksOutputModel(BaseModel):
    description: str
    summary: str
    expected_output: str
    raw: str
