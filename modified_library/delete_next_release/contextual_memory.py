from typing import Optional, Dict, Any

from crewai.memory import EntityMemory, LongTermMemory, ShortTermMemory, UserMemory

from helpers.logger_config import logger # modified
from redis_logs import PipelineAILogs # modified

from helpers.redis_client import redis_client

class ContextualMemory:
    def __init__(
        self,
        memory_config: Optional[Dict[str, Any]],
        stm: ShortTermMemory,
        ltm: LongTermMemory,
        em: EntityMemory,
        um: UserMemory,
    ):

        self.redis_client = redis_client

        if memory_config is not None:
            self.memory_provider = memory_config.get("provider")
        else:
            self.memory_provider = None
        self.stm = stm
        self.ltm = ltm
        self.em = em
        self.um = um

    def build_context_for_task(self, task, context) -> str:
        """
        Automatically builds a minimal, highly relevant set of contextual information
        for a given task.
        """

        query = f"{task.description} {context}".strip()

        if query == "":
            return ""

        context = []
        context.append(self._fetch_ltm_context(task.description))
        context.append(self._fetch_stm_context(query))
        context.append(self._fetch_entity_context(query))
        if self.memory_provider == "mem0":
            context.append(self._fetch_user_context(query))
            
        # modified
        logger.info("Combined Memory/Contextual Context:\n %s", "\n".join(filter(None, context))) 
        contextual_memory = "\n".join(filter(None, context))
        PipelineAILogs().publishLogs(f"Combined Memory/Contextual Context: {contextual_memory}", "purple",redisClient=self.redis_client )
        # modified
        
        return "\n".join(filter(None, context))

    def _fetch_stm_context(self, query) -> str:
        """
        Fetches recent relevant insights from STM related to the task's description and expected_output,
        formatted as bullet points.
        """
        
        stm_results = self.stm.search(query)
        formatted_results = "\n".join(
            [
                f"- {result['memory'] if self.memory_provider == 'mem0' else result['context']}"
                for result in stm_results
            ]
        )
        
        # modified
        logger.info("Short-Term Memory Search Results:\n %s", formatted_results)
        PipelineAILogs().publishLogs(f"Short-Term Memory Search Results: {formatted_results}", "purple",redisClient=self.redis_client )
        # modified
        
        return f"Recent Insights:\n{formatted_results}" if stm_results else ""

    def _fetch_ltm_context(self, task) -> Optional[str]:
        """
        Fetches historical data or insights from LTM that are relevant to the task's description and expected_output,
        formatted as bullet points.
        """
        ltm_results = self.ltm.search(task, latest_n=2)
        if not ltm_results:
            # modified
            logger.info("Long-Term Memory Search Results: None")
            PipelineAILogs().publishLogs(f"Long-Term Memory Search Results: None", "purple",redisClient=self.redis_client )
            # modified
            return None

        formatted_results = [
            suggestion
            for result in ltm_results
            for suggestion in result["metadata"]["suggestions"]  # type: ignore # Invalid index type "str" for "str"; expected type "SupportsIndex | slice"
        ]
        formatted_results = list(dict.fromkeys(formatted_results))
        formatted_results = "\n".join([f"- {result}" for result in formatted_results])  # type: ignore # Incompatible types in assignment (expression has type "str", variable has type "list[str]")

        # modified
        logger.info("Long-Term Memory Search Results:\n %s", formatted_results)
        PipelineAILogs().publishLogs(f"Long-Term Memory Search Results: {formatted_results}", "purple",redisClient=self.redis_client )
        # modified

        return f"Historical Data:\n{formatted_results}" if ltm_results else ""

    def _fetch_entity_context(self, query) -> str:
        """
        Fetches relevant entity information from Entity Memory related to the task's description and expected_output,
        formatted as bullet points.
        """
        # modified
        logger.info("Searching Entity Memory.....") 
        PipelineAILogs().publishLogs("Searching Entity Memory.....", "purple",redisClient=self.redis_client )
        # modified
        
        em_results = self.em.search(query)
        formatted_results = "\n".join(
            [
                f"- {result['memory'] if self.memory_provider == 'mem0' else result['context']}"
                for result in em_results
            ]  # type: ignore #  Invalid index type "str" for "str"; expected type "SupportsIndex | slice"
        )
        
        # modified
        logger.info("Entity Memory Search Results:\n %s", formatted_results)
        PipelineAILogs().publishLogs(f"Entity Memory Search Results: {formatted_results}", "purple",redisClient=self.redis_client )
        # modified
        
        return f"Entities:\n{formatted_results}" if em_results else ""

    def _fetch_user_context(self, query: str) -> str:
        """
        Fetches and formats relevant user information from User Memory.
        Args:
            query (str): The search query to find relevant user memories.
        Returns:
            str: Formatted user memories as bullet points, or an empty string if none found.
        """
        user_memories = self.um.search(query)
        if not user_memories:
            return ""

        formatted_memories = "\n".join(
            f"- {result['memory']}" for result in user_memories
        )
        
        # modified
        logger.info("User Memory Search Results:\n %s \n", formatted_memories)
        PipelineAILogs().publishLogs(f"User Memory Search Results: {formatted_memories}", "purple",redisClient=self.redis_client )
        # modified
        
        return f"User memories/preferences:\n{formatted_memories}"
