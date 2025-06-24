from pydantic import BaseModel

class TestTool(BaseModel):
    class_name:str
    class_definition:str
    inputs:dict = {}