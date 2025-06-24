import os
from distutils.util import strtobool
from typing import Optional,Type,Any
import asyncio # Added
# import aiofiles # Added

from pydantic import BaseModel, Field
from crewai.tools.structured_tool import CrewStructuredTool
from crewai.tools.base_tool import BaseTool



class FileWriterRequest(BaseModel):
    filename: str = Field(
        ...,
        description="Name of the file to be created or overwritten. Must include the file extension (e.g., 'notes.txt')."
    )
    content: str = Field(
        ...,
        description="Text content to be written into the file."
    )
    # overwrite: str = Field(
    #     default="False",
    #     description="Set to 'True' to allow overwriting existing files. Defaults to 'False'."
    # )
    directory: str = Field(
        default="",
        description="Relative directory path where the file should be saved, e.g., 'logs/'. Uses current working directory if not specified."
    )


class FileWriterTool(BaseTool):
    name: str = "File Writer"
    description: str = """Writes text content to a specified file in a given directory.
    
    Required inputs:
    - 'filename': Name of the file to create or overwrite. Must include file extension.
    - 'content': The text content to be written.
    
    Optional inputs:
    - 'directory': Target subdirectory from the current working directory.

    Returns a confirmation message or an error if the file exists and overwrite is disabled.
    """
    # - 'overwrite': Set to 'True' to overwrite if the file already exists.
    base_dir: str = os.getcwd()
    args_schema: Type[BaseModel] = FileWriterRequest

    # def __init__(self, base_dir: str):
    #     self.base_dir = base_dir

    def _write_file(
        self,
        filename: str,
        content: str,
        #overwrite: str = "False",
        directory: str = ""
    ) -> str:
        try:
            # Ensure directory exists
            target_dir = os.path.normpath(os.path.join(self.base_dir, directory))
            
            if self.base_dir not in target_dir:
                raise ValueError(f"Wrong Parent Directory!! Always use the directory '{self.base_dir}' for creating files and subdirectories.")
            
            os.makedirs(target_dir, exist_ok=True)

            filepath = os.path.join(target_dir, filename)

            # Interpret the overwrite flag
            # allow_overwrite = bool(strtobool(overwrite))

            # if os.path.exists(filepath) and not allow_overwrite:
            #     return f"File '{filepath}' already exists and overwrite option is disabled."

            mode = "w" #if allow_overwrite else "x"
            with open(filepath, mode) as file:
                file.write(content)

            # mode = "w" if allow_overwrite else "x"
            # # Use aiofiles for async file operations
            # async with aiofiles.open(filepath, mode=mode) as file: # Changed to async with aiofiles.open
            #     await file.write(content) # Added await

            return f"Content successfully written to '{filepath}'."
        except FileExistsError:
            return f"File '{filepath}' already exists and overwrite option is disabled."
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def _run(self, **kwargs: Any) -> str:
        filename = kwargs.get('filename')
        content = kwargs.get('content')
        directory = kwargs.get('directory', '')
        return self._write_file(filename, content, directory)

    async def _arun(self, **kwargs: Any) -> str:
        filename = kwargs.get('filename')
        content = kwargs.get('content')
        directory = kwargs.get('directory', '')
        # Async wrapper for compatibility; doesn't add concurrency to file I/O but useful for async workflows
        return await self._write_file(filename, content, directory)


# def get_file_writer_tool(base_dir: str) -> CrewStructuredTool:
#     return CrewStructuredTool.from_function(
#         name=FileWriterTool.name,
#         description=FileWriterTool.description,
#         func=FileWriterTool(base_dir=base_dir).run,
#         coroutine=FileWriterTool(base_dir=base_dir).arun,
#         args_schema=FileWriterRequest,
#     )