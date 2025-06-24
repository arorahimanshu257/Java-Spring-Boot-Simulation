from typing import Optional
from pydantic import BaseModel

class LangFuse(BaseModel):
    langfuseHost: Optional[str] = None
    langfusePublicKey: Optional[str] = None
    langfuseSecretKey: Optional[str] = None
