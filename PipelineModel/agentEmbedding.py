from pydantic import BaseModel
from typing import Optional

class AgentEmbedding(BaseModel):
    # Azure embedding config
    embedding_model: Optional[str] = None
    embedding_deployment_name: Optional[str] = None
    embedding_api_version: Optional[str] = None
    embedding_api_key: Optional[str] = None
    embedding_azure_endpoint: Optional[str] = None

    # Amazon embedding config
    embedding_aws_key: Optional[str] = None
    embedding_aws_secret_key: Optional[str] = None
    embedding_aws_region: Optional[str] = None
    embedding_model_id: Optional[str] = None

    # Google embedding config
    embedding_gcp_location: Optional[str] = None
    embedding_gcp_project_id: Optional[str] = None

    # Chroma DB config
    aiEngine: Optional[str] = None
    chroma_end_point: Optional[str] = None
    chroma_port: Optional[str] = None
    index_collection: Optional[str] = None