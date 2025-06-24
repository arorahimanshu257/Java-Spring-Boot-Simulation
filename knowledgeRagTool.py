from typing import Optional, Any, List
import chromadb
from crewai.tools.base_tool import BaseTool
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from PipelineModel.agentEmbedding import AgentEmbedding
import boto3
from langchain_community.embeddings.bedrock import BedrockEmbeddings
import os
from fastapi import HTTPException

from redis_logs import PipelineAILogs
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from helpers.logger_config import logger
from helpers.redis_client import redis_client
from helpers.helpers import parent_doc_retriever

USE_BEDROCK_CREDENTIALS = os.getenv("USE_BEDROCK_CREDENTIALS", 'True')

logger.info('Knowledge Base is starting up')

class FixedKnowledgeRAGToolSchema(BaseModel):
    """Input for KnowledgeRAGTool."""

    pass


class KnowledgeRAGToolSchema(FixedKnowledgeRAGToolSchema):
    """Input for ScrapeWebsiteTool."""

    input: str = Field(..., description="input to search from vector database")
    agentEmbedding: Optional[List[AgentEmbedding]] = Field(
        default=None, description="Embedding LLM Details")
    
class KnowledgeRAGTool(BaseTool):
    name: str = "Retrieve knowledge from vector database"
    description: str = "A tool to be used to retrieve knowledge from vector database using a description"
    input: Optional[str] = None
    agentEmbedding: Optional[List[AgentEmbedding]] = None
    chroma_client:str = ""
    args_schema: Type[BaseModel] = KnowledgeRAGToolSchema

    def __init__(
        self,
        input: Optional[str] = None,
        agentEmbedding: Optional[List[AgentEmbedding]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        if input is not None:
            self.args_schema = FixedKnowledgeRAGToolSchema
            self.input = input
            self.agentEmbedding = agentEmbedding
            self.description = f"A tool that can be used to read {input}'s content from knowledge base."
            self._generate_description()

    def _run(
        self,
        **kwargs: Any,
    ) -> Any:
               
        try:
            logger.info("Knowledge Base input is: %s", self.input)
            PipelineAILogs().publishLogs("Knowledge Base input is: "+str(self.input), "green", redisClient=redis_client)
            logger.info("Knowledge Base KArguments is: %s", kwargs)
            docs = []

            for embedding in self.agentEmbedding:

                logger.info("Knowledge Base AIEngine is: %s", embedding.aiEngine)

                if embedding.aiEngine == 'AzureOpenAI':
                    try:
                        embedding_fn = AzureOpenAIEmbeddings(
                            model=embedding.embedding_model,
                            azure_deployment=embedding.embedding_deployment_name,
                            openai_api_version=embedding.embedding_api_version,
                            api_key=embedding.embedding_api_key,
                            azure_endpoint=embedding.embedding_azure_endpoint
                        )
                    except Exception as azure_error:
                        logger.error("Error initializing AzureOpenAI embedding: %s", str(azure_error))
                        raise HTTPException(status_code=500, detail=f"AzureOpenAI embedding initialization failed: {str(azure_error)}")

                elif embedding.aiEngine == 'AmazonBedrock':
                    try:
                        if USE_BEDROCK_CREDENTIALS.lower() == 'true':
                            logger.debug("Bedrock Credentials are used. %s", USE_BEDROCK_CREDENTIALS)
                            boto3_bedrock_runtime_embedding = boto3.client(
                                service_name='bedrock-runtime',
                                region_name=embedding.embedding_aws_region,
                                aws_access_key_id=embedding.embedding_aws_key,
                                aws_secret_access_key=embedding.embedding_aws_secret_key
                            )
                        else:
                            logger.debug("Bedrock Credentials are not used. %s", USE_BEDROCK_CREDENTIALS)
                            boto3_bedrock_runtime_embedding = boto3.client(
                                service_name='bedrock-runtime',
                                region_name=embedding.embedding_aws_region
                            )

                        embedding_fn = BedrockEmbeddings(
                            model_id=embedding.embedding_model_id,
                            client=boto3_bedrock_runtime_embedding
                        )
                    except Exception as bedrock_error:
                        logger.error("Error initializing AmazonBedrock embedding: %s", str(bedrock_error))
                        raise HTTPException(status_code=500, detail=f"AmazonBedrock embedding initialization failed: {str(bedrock_error)}")

                elif embedding.aiEngine == 'GoogleAI':
                    try:
                        embedding_fn = VertexAIEmbeddings(
                            location=embedding.embedding_gcp_location,
                            project=embedding.embedding_gcp_project_id,
                            model_name=embedding.embedding_model_id
                        )
                    except Exception as google_error:
                        logger.error("Error initializing GoogleAI embedding: %s", str(google_error))
                        raise HTTPException(status_code=500, detail=f"GoogleAI embedding initialization failed: {str(google_error)}")

                else:
                    logger.error("AIEngine is not assigned: %s", embedding)
                    raise HTTPException(status_code=500, detail="AIEngine is not assigned")

                logger.info("Knowledge Base Embedding: %s", embedding)

                # Initialize Chroma vector database

                if self.chroma_client:

                    remote_db = self.chroma_client

                else:
                    remote_db = chromadb.HttpClient(host=embedding.chroma_end_point, port=embedding.chroma_port)
                    self.chroma_client = remote_db                
                    logger.info("Knowledge Remote DB: %s", remote_db)

                # Vector store representation
                vectorstore = Chroma(client=remote_db, collection_name=embedding.index_collection, embedding_function=embedding_fn)
                
                logger.info("Knowledge Vector Store ============= %s", vectorstore)

                schema = {}

                metadata = vectorstore.get(limit=1)["metadatas"]

                if len(metadata) == 0:

                    logger.info("Knowledgebase is empty!")

                    PipelineAILogs().publishLogs(f"Knowledgebase is empty", "blue",redisClient=redis_client)

                else:
                    schema = metadata[0]

                if "parent_text" in schema:

                    docs_temp = vectorstore.similarity_search(self.input)
                    
                    docs.extend(parent_doc_retriever(docs_temp))
                
                else:

                    docs.extend(vectorstore.similarity_search(self.input))

                logger.info("Knowledgebase Search Result is: %s", docs)

                PipelineAILogs().publishLogs(f"Knowledgebase Search Result is: {docs}", "green",redisClient=redis_client)
            
            return docs
        
        except Exception as e:
            logger.error("Knowledge Base Tool error is %s", str(e))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red", redisClient=redis_client)
            raise HTTPException(status_code=500, detail="Knowledge Base Tool error is " + str(e))