from typing import Any, Dict, List

from crewai.memory.long_term.long_term_memory_item import LongTermMemoryItem
from crewai.memory.memory import Memory
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage

from helpers.logger_config import logger # modified
from redis_logs import PipelineAILogs # modified
from helpers.redis_client import redis_client

class LongTermMemory(Memory):
    """
    LongTermMemory class for managing cross runs data related to overall crew's
    execution and performance.
    Inherits from the Memory class and utilizes an instance of a class that
    adheres to the Storage for data storage, specifically working with
    LongTermMemoryItem instances.
    """

    def __init__(self, storage=None, path=None):

        self.redis_client = redis_client

        if not storage:
            storage = LTMSQLiteStorage(db_path=path) if path else LTMSQLiteStorage()
        super().__init__(storage)

    def save(self, item: LongTermMemoryItem) -> None:  # type: ignore # BUG?: Signature of "save" incompatible with supertype "Memory"
        
        metadata = item.metadata
        metadata.update({"agent": item.agent, "expected_output": item.expected_output})
        self.storage.save(  # type: ignore # BUG?: Unexpected keyword argument "task_description","score","datetime" for "save" of "Storage"
            task_description=item.task,
            score=metadata["quality"],
            metadata=metadata,
            datetime=item.datetime,
        )
        
        # modified
        log_message = {
            "task_description": item.task,
            "quality_score": metadata["quality"],
            "metadata": metadata,
            "datetime": str(item.datetime)
        }
        logger.info("Details Saved in Long-Term Memory: \n%s", log_message)
        PipelineAILogs().publishLogs(f"Details Saved in Long-Term Memory: {log_message}", "purple",redisClient=self.redis_client )
        # modified

    def search(self, task: str, latest_n: int = 3) -> List[Dict[str, Any]]:  # type: ignore # signature of "search" incompatible with supertype "Memory"
    
        # modified
        logger.info("Searching Long-Term Memory.....")
        PipelineAILogs().publishLogs("Searching Long-Term Memory.....", "purple",redisClient=self.redis_client )
        # modified
        
        return self.storage.load(task, latest_n)  # type: ignore # BUG?: "Storage" has no attribute "load"

    def reset(self) -> None:
        self.storage.reset()
