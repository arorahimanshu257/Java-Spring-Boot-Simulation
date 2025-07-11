from typing import Any, Optional, Type


class InternalInstructor:
    """Class that wraps an agent llm with instructor."""

    def __init__(
        self,
        content: str,
        model: Type,
        agent: Optional[Any] = None,
        llm: Optional[str] = None,
        instructions: Optional[str] = None,
    ):
        self.content = content
        self.agent = agent
        self.llm = llm
        self.instructions = instructions
        self.model = model
        self._client = None
        self.set_instructor()

    def set_instructor(self):
        """Set instructor."""
        if self.agent and not self.llm:
            self.llm = self.agent.function_calling_llm or self.agent.llm

        # Lazy import
        import instructor
        from litellm import completion

        self._client = instructor.from_litellm(
            completion,
            mode=instructor.Mode.TOOLS,
        )

    def to_json(self):
        model = self.to_pydantic()
        return model.model_dump_json(indent=2)

    def to_pydantic(self):
        messages = [{"role": "user", "content": self.content}]
        if self.instructions:
            messages.append({"role": "system", "content": self.instructions})
        #modified
        model = self._client.chat.completions.create(
            model=self.llm.model, response_model=self.model, messages=messages, api_base=self.llm.base_url, api_version=self.llm.api_version, api_key=self.llm.api_key, aws_access_key_id=self.llm.kwargs.get("aws_access_key_id"), aws_secret_access_key=self.llm.kwargs.get("aws_secret_access_key"),aws_region_name=self.llm.kwargs.get("aws_region_name")
        ) 
        # modified
        return model
