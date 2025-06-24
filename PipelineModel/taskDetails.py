from typing import Optional
from pydantic import BaseModel

class TaskDetails(BaseModel):
    description: Optional[str] = None
    expectedOutput: Optional[str] = None
