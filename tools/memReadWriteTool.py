from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from helpers.logger_config import logger
from helpers.redis_client import redis_client
from redis_logs import PipelineAILogs


class FixedMemoryReaderWriterTool(BaseModel):
    """Input for MemoryReaderWriterTool."""


class MemoryReaderWriterToolSchema(FixedMemoryReaderWriterTool):
    """Input for MemoryReaderWriterTool."""


class MemoryReaderWriterTool(BaseTool):
    name: str = "Memory Reader Writer Tool"
    description: str = (
        "Reads the content of a specified file containing the previous agent's outputs"
        "and returns it as a string. The content of the file readed will be used as context to execute the current task."
    )
    args_schema: Type[BaseModel] = MemoryReaderWriterToolSchema
    execution_id: Optional[str] = None

    def __init__(
        self,
        execution_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if execution_id is not None:
            self.execution_id = execution_id
        
    def _run(
        self,
        **kwargs: Any,
    ) -> Any:
        key = self.execution_id + '_memory'
        
        logger.info(f"Attempting to read memory from Redis with execution_id: {key}")
        PipelineAILogs().publishLogs(f"Attempting to read memory from Redis with execution_id: {key}", "green", redisClient=redis_client)

        if redis_client.exists(key):
            content = redis_client.get(key)
            PipelineAILogs().publishLogs(f"Successfully retrieved memory contents for execution_id {key}. Contents: \n{content}", "green", redisClient=redis_client)
            logger.info(f"Successfully retrieved memory contents for execution_id {key}. Contents:\n{content}")
        else:
            content = 'None'
            PipelineAILogs().publishLogs(f"No memory contents found for execution_id {key}.", "green", redisClient=redis_client)
            logger.warning(f"No memory contents found for execution_id {key}.")
        return content