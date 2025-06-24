from typing import Optional, List
from pydantic import BaseModel


class Document(BaseModel):
    page_content: str
    metadata: dict

class ResponseModel:
    input: Optional[str] = None
    answer: Optional[str] = None
    context: Optional[List[Document]] = None