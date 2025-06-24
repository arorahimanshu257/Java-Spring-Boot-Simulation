from zipfile import ZipFile
import zipfile
import os
import shutil
import io
import stat
import errno
import openai
import litellm
import json
from helpers.helpers import zip_and_upload_folder, PatchedBedrockLLM
from crewai_tools.tools.scrape_website_tool.scrape_website_tool import ScrapeWebsiteTool
from crewai_tools.tools.serper_dev_tool.serper_dev_tool import SerperDevTool
# from crewai.tools.structured_tool import CrewStructuredTool
# from modified_library.file_writer_tool import get_file_writer_tool
from knowledgeRagTool import KnowledgeRAGTool
from helpers.db_uri import encode_db_uri
from tools.sqltool import SQLTool
from typing import Dict, Any
from fastapi import UploadFile, File, HTTPException
from PipelineModel.PipelineModel import PipelineModel
from PipelineModel.agentDetails import AgentDetails
from helpers.logger_config import logger
from crewai import Agent, Task, Crew, Process, LLM
from redis_logs import PipelineAILogs
from langfuse.callback import CallbackHandler
from crewai_tools import DirectoryReadTool
from tools.filereadtool import FileReadTool
from tools.memReadWriteTool import MemoryReaderWriterTool
from crewai.agents.parser import AgentFinish
from helpers.helpers import create_embedder
from modified_library.file_writer_tool import FileWriterTool
from tools.image_tool import Imagetool

import chardet
from helpers.redis_client import redis_client

USE_BEDROCK_CREDENTIALS = os.getenv("USE_BEDROCK_CREDENTIALS", 'True')

class PipelineFiles:
    
    logger = logger

    redis_client = redis_client

    # Tool instruction strings
    TOOL_INSTRUCTIONS = {
        "FileWriterTool": "\n\nYou have access to the FileWriterTool. It is advised to use this tool when you have access to it irrespective of whether it's mentioned above to generate or create files explicitly.",
        "SerperDevTool": "\n\nYou have access to the SerperDevTool for web search. It is advised to use this tool when you have access to it irrespective of whether a web search task has been assigned explicitly.",
        "NL2SQLTool": "\n\nYou have access to the NL2SQLTool. It is advised to use this tool when you have access to it irrespective of whether a SQL task has been assigned explicitly.",
        "ScrapeWebsiteTool": "\n\nYou have access to the ScrapeWebsiteTool. It is advised to use this tool when you have access to it irrespective of whether a scraping task has been assigned explicitly.",
        "MemoryReaderWriterTool": "\n\nYou have access to the MemoryReaderWriterTool. It is advised to use this tool when you have access to it irrespective of whether a memory reading/writing task has been assigned explicitly.",
        "KnowledgeRAGTool": "\n\nYou have access to the KnowledgeRAGTool. It is advised to use this tool when you have access to it irrespective of whether a knowledge retrieval task has been assigned explicitly."
    }

    def __init__(self):

        self.logger.info('Files API is starting up')

    async def execute_pipeline_files(self, payload: PipelineModel, access_key: str, files: list[UploadFile] = File(...)):
        
        try:
            response = None

            self.logger.info("Current Directory: %s", os.getcwd())
            # Generate random subfolder name
            random_name = payload.executionId #''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            self.logger.info("Subfolder name: %s", random_name)
            subfolder_path = os.path.join(os.getcwd(), random_name)
            self.logger.info("Subfolder path: %s", subfolder_path)

            # Create the subfolder
            os.makedirs(subfolder_path, exist_ok=True)
            os.chmod(subfolder_path, 777)
            zip_files = [file for file in files if file.filename.endswith(".zip")]
        except Exception as e:
            self.logger.error("Error while creating subfolder: %s", str(e))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail=str(e))

        if not zip_files:
            raise HTTPException(status_code=400, detail = "Zip file not found, please upload a valid zip file")

        # Process uploaded files
        try:           
            for idx, file in enumerate(zip_files):
                self.logger.info("Unzipping file...")

                try:
                    zip_bytes = await file.read()

                    # Create a subfolder for each zip with the same name as the zip file
                    zip_folder_name = f"{os.path.splitext(file.filename)[0]}"
                    zip_subfolder_path = os.path.join(subfolder_path, zip_folder_name)
                    os.chmod(subfolder_path, 0o777)
                    os.makedirs(zip_subfolder_path, exist_ok=True)

                    with ZipFile(io.BytesIO(zip_bytes), "r") as zip_ref:
                        for file_info in zip_ref.infolist():
                            filename = file_info.filename

                            if not self.is_hidden(filename):
                                extracted_path = zip_ref.extract(file_info, zip_subfolder_path)
                                os.chmod(extracted_path, 0o777)
                                self.logger.info("Extracted: %s", filename)
                            else:
                                self.logger.info("Skipped hidden: %s", filename)
                
                except zipfile.BadZipFile as e:
                    self.logger.error("Invalid zip file: %s", str(e))
                    PipelineAILogs().publishLogs(f"DA Pipeline Exception: Invalid zip file - {str(e)}", "red", redisClient=self.redis_client)
                    raise HTTPException(status_code=400, detail=f"DA Pipeline Exception: Invalid zip file - {str(e)}")
                
                except PermissionError as e:
                    self.logger.error("Not enough permissisons to open the file: %s", str(e))
                    PipelineAILogs().publishLogs(f"Not enough permissisons to open the file - {str(e)}", "red", redisClient=self.redis_client)
                    raise HTTPException(status_code=400, detail=f"DA Pipeline Exception: Invalid zip file - {str(e)}")

                except MemoryError as e:
                    self.logger.error("Invalid zip file: %s", str(e))
                    PipelineAILogs().publishLogs(f"DA Pipeline Exception: Invalid zip file - {str(e)}", "red", redisClient=self.redis_client)
                    raise HTTPException(status_code=400, detail=f"DA Pipeline Exception: Invalid zip file - {str(e)}")

                except Exception as e:
                    self.logger.error("Error extracting zip file: %s", str(e))
                    raise HTTPException(status_code=500, detail=f"Error extracting zip file: {str(e)}")

            langfuse_config = self.setup_langfuse(payload)

            response = await self.execute_pipeline_logic_files(payload, langfuse_config, subfolder_path, access_key=access_key)
            
            self.logger.info("Final Pipeline files Response.......... %s", response)

            return response

        except Exception as e:
            self.logger.error("Error from Pipeline files execution ------- %s", str(e))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red",redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail=str(e))
        
        finally:
            self.logger.info("Deleting subfolder: %s", subfolder_path)

            # Ignore errors if folder doesn't exist
            try:
                if os.path.exists(subfolder_path):
                    shutil.rmtree(subfolder_path, ignore_errors=False, onerror=self.remove_readonly)
            except Exception as e:
                self.logger.error("Error Deleting zip file: %s", str(e))
                PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red",redisClient=self.redis_client)



    def setup_langfuse(self, payload):
        langfuse_metadata = {
            "trace_name": payload.name,  # set langfuse Trace Name
            "trace_id": payload.executionId,         # set langfuse Trace ID
            "trace_user_id": payload.user,       # set langfuse Trace User ID
            "tags": ["Workflow"]            # set langfuse Tags
        }
        return langfuse_metadata

    def is_hidden(self, filepath):
        # For Unix-like systems: hidden files start with a dot
        self.logger.info("Basename is =============== %s", os.path.basename(filepath))
        return os.path.basename(filepath).startswith('.')


    def remove_readonly(self, func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:

            # ensure parent directory is writeable too
            pardir = os.path.abspath(os.path.join(path, os.path.pardir))
            if not os.access(pardir, os.W_OK):
                os.chmod(pardir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise

    async def execute_pipeline_logic_files(self, payload: PipelineModel, langfuse_config, subfolder_path,access_key):
        try:
            agents = []
            tasks = []

            for agent_data in payload.pipeLineAgents:
                agent, task = await self.setup_agents_files(agent=agent_data.agent, userInputs=payload.userInputs, memory=payload.enableAgenticMemory, langfuse_config=langfuse_config,
                                                            subfolder_path=subfolder_path,executionId=payload.executionId)
                agents.append(agent)
                tasks.append(task)

            manager_llm = None
            if payload.managerLlm:
                if payload.managerLlm.aiEngine == 'AmazonBedrock':
                    self.logger.info("Inside AmazonBedrock Block............")
                    
                    if USE_BEDROCK_CREDENTIALS == 'True' or USE_BEDROCK_CREDENTIALS == 'true':
                        logger.debug("Bedrock Credentials are used. %s", USE_BEDROCK_CREDENTIALS)
                        
                        if 'llama' in payload.managerLlm.bedrockModelId.lower():
                            logger.debug("Using Patched Bedrock LLM for Llama model")
                            manager_llm = PatchedBedrockLLM(
                                model="bedrock/" + payload.managerLlm.bedrockModelId,
                                aws_access_key_id=payload.managerLlm.accessKey,
                                aws_secret_access_key=payload.managerLlm.secretKey,
                                aws_region_name=payload.managerLlm.region,
                                max_tokens = payload.managerLlm.maxToken,
                                temperature = payload.managerLlm.temperature,
                                top_p = payload.managerLlm.topP,
                            )
                            
                        else:
                            logger.debug("Using standard Bedrock LLM")
                            manager_llm = LLM(
                                model="bedrock/" + payload.managerLlm.bedrockModelId,
                                aws_access_key_id=payload.managerLlm.accessKey,
                                aws_secret_access_key=payload.managerLlm.secretKey,
                                aws_region_name=payload.managerLlm.region,
                                temperature=payload.managerLlm.temperature,
                                top_p=payload.managerLlm.topP,
                                max_tokens=payload.managerLlm.maxToken,
                                metadata=langfuse_config,
                            )
                    else:
                        logger.debug("Bedrock Credentials are not used. %s", USE_BEDROCK_CREDENTIALS)
                        manager_llm = LLM(
                            model="bedrock/" + payload.managerLlm.bedrockModelId,
                            aws_region_name=payload.managerLlm.region,
                            temperature=payload.managerLlm.temperature,
                            top_p=payload.managerLlm.topP,
                            max_tokens=payload.managerLlm.maxToken,
                            metadata=langfuse_config,
                        )
                elif payload.managerLlm.aiEngine == 'AzureOpenAI':
                    self.logger.info("Inside AzureOpenAI Block............")
                    if "o1" in payload.managerLlm.model or "o3" in payload.managerLlm.model:
                        manager_llm = LLM(
                            model="azure/" + payload.managerLlm.llmDeploymentName,
                            base_url=payload.managerLlm.azureEndpoint,
                            api_key=payload.managerLlm.apiKey,
                            api_version=payload.managerLlm.llmApiVersion,
                            metadata=langfuse_config,
                        )
                    elif "deepseek" in payload.managerLlm.model.lower():
                        manager_llm = LLM(
                            model=payload.managerLlm.model,
                            temperature=payload.managerLlm.temperature,
                            max_tokens=payload.managerLlm.maxToken,
                            base_url=payload.managerLlm.azureEndpoint,
                            api_key=payload.managerLlm.apiKey,
                            metadata=langfuse_config,
                        )
                    else:
                        manager_llm = LLM(
                            model="azure/" + payload.managerLlm.llmDeploymentName,
                            temperature=payload.managerLlm.temperature,
                            max_tokens=payload.managerLlm.maxToken,
                            base_url=payload.managerLlm.azureEndpoint,
                            api_key=payload.managerLlm.apiKey,
                            api_version=payload.managerLlm.llmApiVersion,
                            metadata=langfuse_config,
                        )
                elif payload.managerLlm.aiEngine == 'GoogleAI':
                    self.logger.info("Inside GoogleAI Block............")
                    manager_llm = LLM(
                        model="vertex_ai/" + payload.managerLlm.model,
                        gcp_project_id=payload.managerLlm.gcpProjectId,
                        temperature=payload.managerLlm.temperature,
                        max_tokens=payload.managerLlm.maxToken,
                        location=payload.managerLlm.gcpLocation,
                        metadata=langfuse_config,
                    )
                else:
                    self.logger.error("Unsupported LLM type for manager_llm ----------------- %s", payload.managerLlm.aiEngine)
                    raise ValueError("Unsupported LLM type for manager_llm")

            if manager_llm:
                self.logger.debug("manager llm values  %s", manager_llm)

                if "o1" in payload.managerLlm.model or "o3" in payload.managerLlm.model:
                    manager_agent = Agent(
                        role="Crew Manager",
                        goal="""
                			Manage the team to complete the task in the best way possible.
                			""",
                        backstory="""
                			You are a seasoned manager with a knack for getting the best out of your team.\nYou are also known for your ability to delegate work to the right people, and to ask the right questions to get the best out of your team.\nEven though you don't perform tasks by yourself, you have a lot of experience in the field, which allows you to properly evaluate the work of your team members.

                			Additional rules for Tools:
                			-----------------
                			1. Regarding the Action Input (the input to the action, just a simple python dictionary, enclosed
                			in curly braces, using \" to wrap keys and values.)

                			For example for the following schema:
                			```
                			class ExampleToolInput(BaseModel):
                				task: str = Field(..., description="The task to delegate")
                				context: str = Field(..., description="The context for the task")
                				coworker: str = Field(..., description="The role/name of the coworker to delegate to")
                			```
                			Then the input should be a JSON object with the user ID:
                			- task: The task to delegate
                			- context: The context for the task
                			- coworker: The role/name of the coworker to delegate to
                			""",
                        #callbacks=[langfuse_config],
                        llm=manager_llm,
                        use_system_prompt=False
                    )
                
                elif any(keyword in payload.managerLlm.model for keyword in ["claude", "anthropic", "bedrock"]):
                    manager_agent = Agent(
                        role="Crew Manager",
                        goal="""
                                			Manage the team to complete the task in the best way possible.
                                			""",
                        backstory="""
                                			You are a seasoned manager with a knack for getting the best out of your team.\nYou are also known for your ability to delegate work to the right people, and to ask the right questions to get the best out of your team.\nEven though you don't perform tasks by yourself, you have a lot of experience in the field, which allows you to properly evaluate the work of your team members.

                                			Additional rules for Tools:
                                			-----------------
                                			1. Regarding the Action Input (the input to the action, just a simple python dictionary, enclosed
                                			in curly braces, using \" to wrap keys and values.)

                                			For example for the following schema:
                                			```
                                			class ExampleToolInput(BaseModel):
                                				task: str = Field(..., description="The task to delegate")
                                				context: str = Field(..., description="The context for the task")
                                				coworker: str = Field(..., description="The role/name of the coworker to delegate to")
                                			```
                                			Then the input should be a JSON object with the user ID:
                                			- task: The task to delegate
                                			- context: The context for the task
                                			- coworker: The role/name of the coworker to delegate to
                                			""",
                        #callbacks=[langfuse_config],
                        llm=manager_llm,
                        use_system_prompt= os.getenv("USE_SYSTEM_PROMPT") if os.getenv("USE_SYSTEM_PROMPT") else True
                    )

                else:
                    manager_agent = Agent(
                        role="Crew Manager",
                        goal="""
                                			Manage the team to complete the task in the best way possible.
                                			""",
                        backstory="""
                                			You are a seasoned manager with a knack for getting the best out of your team.\nYou are also known for your ability to delegate work to the right people, and to ask the right questions to get the best out of your team.\nEven though you don't perform tasks by yourself, you have a lot of experience in the field, which allows you to properly evaluate the work of your team members.

                                			Additional rules for Tools:
                                			-----------------
                                			1. Regarding the Action Input (the input to the action, just a simple python dictionary, enclosed
                                			in curly braces, using \" to wrap keys and values.)

                                			For example for the following schema:
                                			```
                                			class ExampleToolInput(BaseModel):
                                				task: str = Field(..., description="The task to delegate")
                                				context: str = Field(..., description="The context for the task")
                                				coworker: str = Field(..., description="The role/name of the coworker to delegate to")
                                			```
                                			Then the input should be a JSON object with the user ID:
                                			- task: The task to delegate
                                			- context: The context for the task
                                			- coworker: The role/name of the coworker to delegate to
                                			""",
                        #callbacks=[langfuse_config],
                        llm=manager_llm,
                    )

                crew = Crew(
                    agents=agents,
                    tasks=tasks,
                    verbose=True,
                    process=Process.hierarchical,
                    manager_agent=manager_agent,
                    memory=payload.enableAgenticMemory,
                    embedder=create_embedder(payload.masterEmbedding) if payload.enableAgenticMemory else None
                )
            else:
                self.logger.debug("manager llm values null Else block ---------->")
                crew = Crew(
                    agents=agents,
                    tasks=tasks,
                    verbose=True,
                    memory=payload.enableAgenticMemory,
                    embedder=create_embedder(payload.masterEmbedding) if payload.enableAgenticMemory else None
                )

            crew_output = crew.kickoff()

            folder_path = os.path.join(os.getcwd(),payload.executionId)
            
            file_id = zip_and_upload_folder(pipelineId=payload.pipelineId,executionId=payload.executionId,user=payload.user,folder_path=folder_path,access_key=access_key)

            PipelineAILogs().publishLogs("DA Pipeline Logs Completed", "green",redisClient=self.redis_client)

            for agent in agents:
                if any(isinstance(tool, FileWriterTool) for tool in agent.tools):
                    return crew_output, file_id
                else:
                    continue

            return crew_output,"Not applicable"

        except openai.BadRequestError as err:
            self.logger.error("Failed to execute Pipeline files ----------------- %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail="Failed to execute Pipeline files: " + str(err))
        
        except litellm.BadRequestError as err:
            self.logger.error("Failed to execute Pipeline files ----------------- %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail="Failed to execute Pipeline files: " + str(err))

        except litellm.AuthenticationError as err:
            self.logger.error("Authentication failed: %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=401, detail="Authentication failed: " + str(err))
        
        except openai.PermissionDeniedError as err:
            self.logger.error("Permission denied: %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=403, detail="Permission denied: " + str(err))
        
        except litellm.NotFoundError as err:
            self.logger.error("Resource not found: %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=404, detail="Resource not found: " + str(err))
        
        except litellm.RateLimitError as err:
            self.logger.error("Rate limit exceeded: %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=429, detail="Rate limit exceeded: " + str(err))
        
        except litellm.APIConnectionError as err:
            self.logger.error("API connection error: %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=503, detail="API connection error: " + str(err))

        except Exception as e:
            self.logger.error("Failed to execute Pipeline files ----------------- %s", str(e))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red",redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail="Failed to execute Pipeline files: " + str(e))
        
        # finally:
        #     execution_folder = os.path.join(os.getcwd(), str(payload.executionId))
        #     if os.path.exists(execution_folder):
        #         try:
        #             shutil.rmtree(execution_folder)
        #             logger.info(f"Successfully deleted folder: {execution_folder}")
        #         except Exception as e:
        #             logger.error(f"Error deleting folder {execution_folder}: {str(e)}")
        #     else:
        #         logger.info(f"Folder not found: {execution_folder}")
    
    def add_dynamic_user_tools(self, class_name, class_definition):
        try:
            # Execute the class definition
            exec(class_definition, globals())
            # Instantiate the class
            tool_instance = globals()[class_name]()
            # Append the tool instance to the agent's tools
            logger.info(f"Dynamic user tool '{class_name}' added successfully.")
            return tool_instance
        except Exception as e:
            logger.error(f"Error adding dynamic user tool: {str(e)}")
            raise HTTPException(status_code=500,detail=f"Error adding dynamic user tool, there's an error in the tool code: {str(e)}")

    async def setup_agents_files(self, agent: AgentDetails, userInputs: Dict[str, str], memory: bool, langfuse_config, subfolder_path,executionId):
        def step_callback_fun(step: Any):
            if isinstance(step, AgentFinish):
                agent_name = step.agent.role
                agent_output = step.output

                # Create the dictionary entry
                entry = {
                    "Agent": agent_name,
                    "Agent_Output": agent_output
                }
                key = executionId + '_memory'

                # Define the prefix message
                prefix = "Here are the outputs of the tasks performed by the agent.\n"

                if redis_client.exists(key):
                    logger.debug("Key already exists, appending to existing list")
                    # Get existing string and extract the JSON part
                    existing_value = redis_client.get(key)
                    json_part = existing_value[len(prefix):]
                    task_list = json.loads(json_part)
                    task_list.append(entry)
                else:
                    logger.debug("Key does not exist, creating new list")
                    task_list = [entry]

                # Reconstruct the full string
                updated_value = prefix + json.dumps(task_list, indent=2)
                redis_client.set(key, updated_value, ex=7200)
                logger.info("Updated task list stored")
        
        try:
            has_image = "{{image" in agent.task.description

            toolbox = []

            if agent.llm.aiEngine == 'AzureOpenAI':
                self.logger.info("Inside AzureOpenAI Block............")
                if "o1" in agent.llm.model or "o3" in agent.llm.model:
                    llm = LLM(
                        model="azure/" + agent.llm.llmDeploymentName,
                        base_url=agent.llm.azureEndpoint,
                        api_key=agent.llm.apiKey,
                        api_version=agent.llm.llmApiVersion,
                        metadata=langfuse_config,
                    )
                elif "deepseek" in agent.llm.model.lower():
                    llm = LLM(
                        model=agent.llm.model,
                        temperature=agent.llm.temperature,
                        max_tokens=agent.llm.maxToken,
                        base_url=agent.llm.azureEndpoint,
                        api_key=agent.llm.apiKey,
                        metadata=langfuse_config,
                    )
                else:
                    llm = LLM(
                        model="azure/" + agent.llm.llmDeploymentName,
                        temperature=agent.llm.temperature,
                        max_tokens=agent.llm.maxToken,
                        base_url=agent.llm.azureEndpoint,
                        api_key=agent.llm.apiKey,
                        api_version=agent.llm.llmApiVersion,
                        metadata=langfuse_config,
                    )
            elif agent.llm.aiEngine == 'AmazonBedrock':
                self.logger.info("Inside AmazonBedrock Block............")
                
                if USE_BEDROCK_CREDENTIALS == 'True' or USE_BEDROCK_CREDENTIALS == 'true':
                    logger.debug("Bedrock Credentials are used. %s", USE_BEDROCK_CREDENTIALS)
                    
                    if 'llama' in agent.llm.bedrockModelId.lower():
                        logger.debug("Using Patched Bedrock LLM for Llama model")
                        
                        llm = PatchedBedrockLLM(
                            model="bedrock/" + agent.llm.bedrockModelId,
                            aws_access_key_id=agent.llm.accessKey,
                            aws_secret_access_key=agent.llm.secretKey,
                            aws_region_name=agent.llm.region,
                            max_tokens=agent.llm.maxToken,
                            temperature=agent.llm.temperature,
                            top_p=agent.llm.topP,
                        )
                        
                    else:
                        logger.debug("Using standard Bedrock LLM")
                        llm = LLM(
                            model="bedrock/" + agent.llm.bedrockModelId,
                            aws_access_key_id=agent.llm.accessKey,
                            aws_secret_access_key=agent.llm.secretKey,
                            aws_region_name=agent.llm.region,
                            temperature=agent.llm.temperature,
                            top_p=agent.llm.topP,
                            max_tokens=agent.llm.maxToken,
                            metadata=langfuse_config,
                        )
                else:
                    logger.debug("Bedrock Credentials are not used. %s", USE_BEDROCK_CREDENTIALS)
                    llm = LLM(
                        model="bedrock/" + agent.llm.bedrockModelId,
                        aws_region_name=agent.llm.region,
                        temperature=agent.llm.temperature,
                        top_p=agent.llm.topP,
                        max_tokens=agent.llm.maxToken,
                        metadata=langfuse_config,
                    )
            elif agent.llm.aiEngine == 'GoogleAI':
                self.logger.info("Inside GoogleAI Block............")
                llm = LLM(
                    model="vertex_ai/" + agent.llm.model,
                    gcp_project_id=agent.llm.gcpProjectId,
                    temperature=agent.llm.temperature,
                    max_tokens=agent.llm.maxToken,
                    location=agent.llm.gcpLocation,
                    metadata=langfuse_config,
                )
            else:
                self.logger.error("Unsupported LLM type ----------------- %s", agent.llm.aiEngine)
                raise HTTPException(status_code=500, detail="Unsupported LLM type" + agent.llm.aiEngine)

            dirTool = DirectoryReadTool(directory=str(subfolder_path))

            file_read_tool = FileReadTool()

            toolbox.append(dirTool)
            toolbox.append(file_read_tool)

            agent_args = {
                "role": agent.role,
                "goal": agent.goal,
                "backstory": agent.backstory,
                #"callbacks": [langfuse_config],
                "llm": llm,
                "function_calling_llm": llm,
                "verbose": agent.verbose,
                "max_iter": 25 if agent.maxIter == 0 else agent.maxIter,
                "max_rpm": None if agent.maxRpm == 0 else agent.maxRpm,
                "max_execution_time": None if agent.maxExecutionTime == 0 else agent.maxExecutionTime,
                "allow_delegation": agent.allowDelegation,
                "memory": memory,
                "cache": False,  # Passing human tools to the agent
                "allow_code_execution": agent.allowCodeExecution,
                "code_execution_mode": "safe" if agent.isSafeCodeExecution else "unsafe",
            }

            # Check if the tool is 'MemoryReaderWriterTool' and add step_callback
            if any(tool.toolName == 'MemoryReaderWriterTool' for tool in agent.tools):
                agent_args["step_callback"] = step_callback_fun

            # Determine the use_system_prompt based on the model
            if "o1" in agent.llm.model or "o3" in agent.llm.model:
                agent_args["use_system_prompt"] = False
            elif any(keyword in agent.llm.model for keyword in ["claude", "anthropic", "bedrock"]):
                agent_args["use_system_prompt"] = os.getenv("USE_SYSTEM_PROMPT", "true").lower() == "true"

            code_conversion_task = agent.task.description

            # Append tool instructions if the tool is present
            tool_names = [tool.toolName for tool in agent.tools]
            if "FileWriterTool" in tool_names:
                code_conversion_task += self.TOOL_INSTRUCTIONS["FileWriterTool"]
            if "SerperDevTool" in tool_names:
                code_conversion_task += self.TOOL_INSTRUCTIONS["SerperDevTool"]
            if "NL2SQLTool" in tool_names:
                code_conversion_task += self.TOOL_INSTRUCTIONS["NL2SQLTool"]
            if "ScrapeWebsiteTool" in tool_names:
                code_conversion_task += self.TOOL_INSTRUCTIONS["ScrapeWebsiteTool"]
            if "MemoryReaderWriterTool" in tool_names:
                code_conversion_task += self.TOOL_INSTRUCTIONS["MemoryReaderWriterTool"]

            for key, value in userInputs.items():
                
                code_conversion_task = code_conversion_task.replace(key, value)
            
            # agent_model.tools.append(dirTool)
            # agent_model.tools.append(file_read_tool)

            if has_image:
                toolbox.append(Imagetool(llm=llm))

            for tool in agent.tools:
                if tool.toolName == 'ScrapeWebsiteTool':
                    scrapeWebsiteTool = None
                    for param in tool.parameters:
                        if param.parameterName == "website_url" and param.value and param.value.strip():
                            scrapeWebsiteTool = ScrapeWebsiteTool(
                                website_url=param.value)
                            toolbox.append(scrapeWebsiteTool)
                    if scrapeWebsiteTool == None:
                        PipelineAILogs().publishLogs("Website URL not provided for scrape website tool.", "red", redisClient=redis_client)
                        raise HTTPException(status_code=500, detail="Website URL not provided for scrape website tool.")
                    logger.info("ScrapeWebsiteTool -------------------- %s", scrapeWebsiteTool)
                    # agent_model.tools.append(scrapeWebsiteTool)
                
                elif tool.toolName == 'MemoryReaderWriterTool':
                    logger.info("MemoryReaderWriterTool being added to the agent")
                    memReadWriteTool = MemoryReaderWriterTool(execution_id=executionId)
                    toolbox.append(memReadWriteTool)
                    # agent_model.tools.append(memReadWriteTool)
                
                elif tool.toolName == 'SerperDevTool':
                    serperDevTool = SerperDevTool()
                    for param in tool.parameters:
                        if (param.parameterName.lower() == "serper_api_key") and (param.value is not None) and (param.value.strip()):
                            os.environ['SERPER_API_KEY'] = param.value

                        elif (param.value is None) or (param.parameterName.lower() == "serper_api_key" and not param.value.strip()):
                            PipelineAILogs().publishLogs("Serper API key not provided for SerperDevTool.", "red", redisClient=redis_client)
                            raise HTTPException(status_code=500, detail="Serper API key not provided for SerperDevTool.")

                    logger.info("SerperDevTool -------------------- %s", serperDevTool)
                    toolbox.append(serperDevTool)
                    # agent_model.tools.append(serperDevTool)

                elif tool.toolName == "FileWriterTool":

                    logger.info("FileWriterTool being added to the agent")

                    base_dir = os.path.join(os.getcwd(), str(executionId))

                    toolbox.append(FileWriterTool(base_dir=base_dir))

                    # file_writer_tool = get_file_writer_tool(base_dir = base_dir)
                    
                    # toolbox.append(file_writer_tool)
                    # agent_model.tools.append(FileWriterTool(base_dir=base_dir))
                    
                elif tool.toolName == 'NL2SQLTool':
                    nl2sql_tool = None
                    for param in tool.parameters:
                        if param.parameterName == "db_uri" and param.value and param.value.strip():
                            encoded_uri = encode_db_uri(param.value)
                            nl2sql_tool=SQLTool(db_uri=encoded_uri)

                    if nl2sql_tool == None:
                        PipelineAILogs().publishLogs("Database URI not provided for NL2SQL tool.", "red", redisClient=redis_client)
                        raise HTTPException(status_code=500, detail="Database URI not provided for NL2SQL tool.")

                    toolbox.append(nl2sql_tool)
                    # agent_model.tools.append(nl2sql_tool)


            for tool in agent.userTools:
                tool_class_name = tool.toolClassName
                logger.debug("user tool class name ------------ %s ",tool_class_name)
                tool_class_definition = tool.toolClassDef
                logger.debug("user tool class def ------------ ")
                tool_instance = self.add_dynamic_user_tools(tool_class_name,tool_class_definition)
                logger.debug("user tool instance created")
                # agent_model.tools.append(tool_instance)
                toolbox.append(tool_instance)
                code_conversion_task += f"\n\nYou have access to the the tool '{tool_class_name}'. It is advised to use this tool when you have access to it irrespective of whether it has been asked to be used explicitly."
            
            if agent.embedding:

                logger.debug("Agent embedding ------------ %s ", agent.embedding)
                code_conversion_task += self.TOOL_INSTRUCTIONS["KnowledgeRAGTool"]

                contextTool = KnowledgeRAGTool(input=code_conversion_task,
                                            agentEmbedding=agent.embedding,
                                            kwargs={"redis_client": redis_client})
                toolbox.append(contextTool)
                # agent_model.tools.append(contextTool)

            agent_args["tools"] = toolbox
            # Create the agent model
            agent_model = Agent(**agent_args)

            task = Task(
                description=code_conversion_task,
                expected_output=agent.task.expectedOutput,
                agent=agent_model
            )
    
            return agent_model, task
        

        except openai.BadRequestError as err:
            self.logger.error("Failed to create Agent ----------------- %s", agent)
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail="Failed to create Agent: " + str(err))
        
        except Exception as e:
            self.logger.error("Failed to create Agent ----------------- %s", agent)
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red", redisClient=self.redis_client)
            raise HTTPException(status_code=500, detail="Failed to create Agent: " + str(e))
