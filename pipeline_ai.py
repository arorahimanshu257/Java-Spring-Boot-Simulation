import json
import httpx
from fastapi import FastAPI, Form, Header, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from helpers.helpers import zip_and_upload_folder
from helpers import agent_image_utils,helpers
from helpers.logger_config import logger
import logging
import os
import openai
from typing import Annotated, Dict, Any
from PipelineModel.PipelineRequest import PipelineRequest
from PipelineModel.PipelineModel import PipelineModel
from PipelineModel.agentDetails import AgentDetails
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools.tools.scrape_website_tool.scrape_website_tool import ScrapeWebsiteTool
from crewai_tools.tools.serper_dev_tool.serper_dev_tool import SerperDevTool
from tools.memReadWriteTool import MemoryReaderWriterTool
from tools.sqltool import SQLTool
from langfuse.callback import CallbackHandler
from pipeline_files import PipelineFiles
from knowledgeRagTool import KnowledgeRAGTool
from langchain_core.exceptions import OutputParserException
from helpers.helpers import create_embedder, PatchedBedrockLLM
from helpers.db_uri import encode_db_uri
from modified_library.file_writer_tool import FileWriterTool
# from crewai.tools.structured_tool import CrewStructuredTool
# from modified_library.file_writer_tool import get_file_writer_tool
from crewai.agents.parser import AgentFinish
from PipelineModel.test_tool import TestTool
from tools.image_tool import Imagetool

import redis
import litellm
from litellm import completion
from helpers.secret_manager import secret_manager
from helpers.redis_client import redis_client
from helpers.pg_client import postgres_client
from redis_logs import PipelineAILogs
import shutil
import stat
import errno

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "genai-platform-creds.json"


# os.environ["ADMIN_URL"] = "https://avaplus-dev.avateam.io/v1/api/admin"

# os.environ["INSTRUCTIONS_URL"] = "https://avaplus-dev.avateam.io/v1/api/instructions"

# os.environ["ENABLE_LOGSTREAMING"] = "True"

# os.environ["USE_SYSTEM_PROMPT"] = "False"

# os.environ['LANGFUSE_PUBLIC_KEY']="pk-lf-cc994203-e833-4309-b754-c6fc4c4de644"
# os.environ['LANGFUSE_SECRET_KEY']="sk-lf-dfd84671-c482-4db8-9493-d54e701c5b54"

# os.environ["LANGFUSE_HOST"]="https://ava-metrics-dev.avateam.io"
litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]

adminUrl = os.getenv('ADMIN_URL')

instructionUrl = os.getenv('INSTRUCTIONS_URL')

USE_BEDROCK_CREDENTIALS = os.getenv("USE_BEDROCK_CREDENTIALS", 'True')

def lifespan(app: FastAPI):
    # Validate required environment variables
    if not os.getenv('ADMIN_URL'):
        logger.error("Environment variable ADMIN_URL is not set")
        raise HTTPException(status_code=500, detail="Environment variable ADMIN_URL is not set. Please add value to the ADMIN_URL environment variable")
    
    if not os.getenv('INSTRUCTIONS_URL'):
        logger.error("Environment variable INSTRUCTIONS_URL is not set")
        raise HTTPException(status_code=500, detail="Environment variable INSTRUCTIONS_URL is not set. Please add value to the INSTRUCTIONS_URL environment variable")

    yield

    if os.getenv("ENABLE_LOGSTREAMING"):
        redis_client.close()
    
    if os.getenv("PERSISTENT_LOGGING"):
        postgres_client.close_all_connections()

logger.info('API is starting up')

app = FastAPI(timeout=6000,lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def health_check():
    logger.debug(
        "Logger enabled for ERROR= %s, WARNING= %s, NFO= %s, DEBUG= %s", logger.isEnabledFor(logging.ERROR),
        logger.isEnabledFor(logging.WARNING),
        logger.isEnabledFor(logging.INFO),
        logger.isEnabledFor(logging.DEBUG)
    )
    return {"status": "healthy"}

@app.get("/platform/pipeline/api/v1/health")
async def health_check_endpoint():

    try:
        return await health_check()
    
    except Exception as e:

        logger.error(f"Unexpected error in health check: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error during health check: {e}")

def initialize_user_tool(class_name, class_definition):
    try:
        local_namespace = {}
        exec(class_definition, local_namespace)
        tool_instance = local_namespace[class_name]()
        return tool_instance
    except Exception as e:
        logger.error(f"Error while initializing the user tool: {str(e)}")
        raise HTTPException(status_code=500,detail=f"Error initializing the user tool, there's an error in the tool code: {str(e)}")

    
@app.post("/force/platform/pipeline/api/v1/test_tool")
async def extract_params(payload:TestTool,access_key: str = Header(None)):

    try:
        
        secret_manager.access_key = access_key

        tool_instance = initialize_user_tool(payload.class_name, payload.class_definition)

        output = tool_instance._run(**payload.inputs)

        return {"status": "success", "output": json.loads(json.dumps(output, default=str))}
    
    except Exception as e:

        raise HTTPException(status_code=500,detail=f"An Error occured while testing the tool code: {e}")


async def execute_pipeline(payload: PipelineModel,access_key: str):
    try:

        langfuse_config = setup_langfuse(payload)
        logger.debug('---------------- Setup LangFuse Config ---------------- ')
        response = await execute_pipeline_logic(payload, langfuse_config, access_key)
        return response

    except Exception as e:
        logger.error(f"Unexpected error in execute_pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during pipeline execution: {e}")


@app.post("/force/platform/pipeline/api/v1/execute")
async def execute(access_key: Annotated[str | None, Header()] = None, pipelineRequest: PipelineRequest = None):
    temporary_images = None

    try:        
        if not pipelineRequest.executionId.strip():
            logger.error("Execution ID is required")
            raise HTTPException(status_code=400, detail="Execution ID is required")

        logStream = os.getenv('ENABLE_LOGSTREAMING')
        persistent_logging = os.getenv("PERSISTENT_LOGGING")

        helpers.save_initial_workflow_history(pipelineRequest.pipeLineId,pipelineRequest.executionId,
                                              pipelineRequest.user, pipelineRequest.model_dump(),adminUrl, access_key)
        if logStream == 'True' or persistent_logging == 'True':
            logger.info("Log stream enabled is -------------- %s", logStream)
            logger.info("Persistent logging is enabled-------------- %s", persistent_logging)

            PipelineAILogs.executionId = pipelineRequest.executionId
            PipelineAILogs.pipelineId = pipelineRequest.pipeLineId
            PipelineAILogs.sender = pipelineRequest.user

        temporary_images, pipelineRequest.userInputs = (
            agent_image_utils.save_temp_images_with_rewrite_inputs(pipelineRequest.userInputs))

        pipelineJson = getPipelinePayload(access_key, pipelineRequest.pipeLineId)
        helpers.save_payload_workflow_history(pipelineRequest.pipeLineId,pipelineRequest.executionId,pipelineJson,adminUrl,access_key)
        logger.info("Pipeline payload is ---------------- %s", pipelineJson)

        payloadObject = PipelineModel(**pipelineJson['pipeline'])
        payloadObject.userInputs = pipelineRequest.userInputs
        payloadObject.executionId = pipelineRequest.executionId
        payloadObject.user = pipelineRequest.user
        secret_manager.access_key = access_key

        logger.debug("Payload after parse json ------- %s", payloadObject)
        logger.debug("Agentic Memory is ---------------- %s", payloadObject.enableAgenticMemory)
    
    except Exception as e:
        logger.error(f"Unexpected error in pipeline execution: {e}")
        helpers.send_execution_status(pipelineRequest.executionId, "FAILED", instructionUrl, access_key)
        raise HTTPException(status_code=500, detail=f"Unexpected error in pipeline execution: {e}")

    try:
        pipelineResponse = await execute_pipeline(payloadObject,access_key)
        logger.debug(" Final response ------- %s", pipelineResponse)

        payloadObject.tasksOutputs = pipelineResponse[0].tasks_output
        payloadObject.output = pipelineResponse[0].raw

        if pipelineResponse[1]=="Not applicable":
            pass

        elif pipelineResponse[1]:
            payloadObject.file_download_url = f"{adminUrl}/ava/force/workflow/history/download-file/" + pipelineResponse[1]

        logger.debug("Final response payload ------- %s", payloadObject)

        helpers.save_final_workflow_history(pipelineRequest.pipeLineId, pipelineRequest.executionId, pipelineResponse,payloadObject, adminUrl, access_key,upload_file_id=pipelineResponse[1])
        
        # Send success status to Java API
        helpers.send_execution_status(pipelineRequest.executionId, "SUCCESS", instructionUrl, access_key)
        
        if pipelineResponse[1]=="Not applicable":
            response = payloadObject.model_dump(exclude={"file_download_url"})
            return {"pipeline":response}
        else:
            return {"pipeline": payloadObject}
            

    except Exception as e:
        logger.error("Error from Pipeline execution ------- %s", str(e))
        PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red", redisClient=redis_client)
        # Send failure status to Java API
        helpers.send_execution_status(pipelineRequest.executionId, "FAILED", instructionUrl, access_key)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        agent_image_utils.clean_up_images(temporary_images)


@app.post("/force/platform/pipeline/api/v1/execute/files")
async def execute(access_key: Annotated[str | None, Header()] = None, files: list[UploadFile] = None, pipeLineId: Annotated[str, Form()] = None, userInputs: Annotated[str, Form()] = None, user: Annotated[str, Form()] = None, executionId: Annotated[str, Form()] = None):

    temporary_images = None  # Add this to track temporary image files
    try:
        if not executionId.strip():
            logger.error("Execution ID is required")
            raise HTTPException(status_code=400, detail="Execution ID is required")

        logStream = os.getenv('ENABLE_LOGSTREAMING')
        persistent_logging = os.getenv("PERSISTENT_LOGGING")
        helpers.save_initial_workflow_history(pipeLineId, executionId, user, userInputs, adminUrl, access_key)        
        if logStream == 'True' or persistent_logging == 'True':
            logger.debug("Log stream enabled is -------------- %s", logStream)
            logger.debug("Persistent logging is enabled-------------- %s", persistent_logging)

            PipelineAILogs.executionId = executionId
            PipelineAILogs.pipelineId = pipeLineId
            PipelineAILogs.sender = user
    
        pipelineJson = getPipelinePayload(access_key, pipeLineId)
        helpers.save_payload_workflow_history(pipeLineId, executionId,pipelineJson,adminUrl,access_key)
        logger.debug("Pipeline payload is ---------------- %s", pipelineJson)

        try:
            userInputs_dict = json.loads(userInputs) if userInputs else {}

            logger.debug(f"Parsed userInput dictionary: {userInputs_dict}")

            temporary_images, userInputs_dict = (
                    agent_image_utils.save_temp_images_with_rewrite_inputs(userInputs_dict))
            logger.debug(f"Processed images in userInputs: {temporary_images}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse userInput: {userInputs}. Error: {str(e)}")
            helpers.send_execution_status(executionId, "FAILED", instructionUrl, access_key)
            raise HTTPException(
                status_code=400,
                detail="Invalid format for userInput. Expected JSON string."
            )

        payloadObject = PipelineModel(**pipelineJson['pipeline'])
        logger.debug("Payload after parse json ------- %s", payloadObject)
        payloadObject.userInputs = userInputs_dict
        payloadObject.user = user
        payloadObject.executionId = executionId
        secret_manager.access_key = access_key

        logger.debug(f"Payload created with userInputs: {payloadObject.userInputs}")

        try:
            pipelineFiles = PipelineFiles()

            pipelineResponse = await pipelineFiles.execute_pipeline_files(payload=payloadObject, files=files, access_key = access_key)

            payloadObject.tasksOutputs = pipelineResponse[0].tasks_output

            payloadObject.output = pipelineResponse[0].raw
            
            if pipelineResponse[1]=="Not applicable":
                pass

            elif pipelineResponse[1]:
                payloadObject.file_download_url = f"{adminUrl}/ava/force/workflow/history/download-file/" + pipelineResponse[1]

            logger.info("Final Pipeline response ------- %s", payloadObject)

            helpers.save_final_workflow_history(pipeLineId, executionId, pipelineResponse, payloadObject, adminUrl, access_key, upload_file_id=pipelineResponse[1])

            # Send success status to Java API
            helpers.send_execution_status(executionId, "SUCCESS", instructionUrl, access_key)

            if pipelineResponse[1]=="Not applicable":
                response = payloadObject.model_dump(exclude={"file_download_url"})
                return {"pipeline":response}
            else:
                return {"pipeline": payloadObject}
            
        except Exception as err:
            logger.error("Error from Pipeline execution ------- %s", str(err))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=redis_client)
            # Send failure status to Java API
            helpers.send_execution_status(executionId, "FAILED", instructionUrl, access_key)
            raise HTTPException(status_code=500, detail=str(err))
     
    except Exception as e:
        logger.error(f"Unexpected error in pipeline execution: {e}")
        helpers.send_execution_status(executionId, "FAILED", instructionUrl, access_key)
        raise HTTPException(status_code=500, detail=f"Unexpected error in pipeline execution: {e}")

    finally:
        # Clean up temporary image files
        if temporary_images:
            agent_image_utils.clean_up_images(temporary_images)
            logger.debug("Cleaned up temporary image files")

def remove_readonly(func, path, exc):
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


def getPipelinePayload(access_key, pipeLineId):

    if not access_key:
        logger.error("Access key is required")
        raise HTTPException(status_code=400, detail="Access key is required")

    logger.debug("access_key ---------------- %s", access_key)
    logger.debug("pipeline id ----------------- %s", pipeLineId)

    params = {'workflowId': pipeLineId}
    logger.debug("params is ----------------- %s", params)

    headers = {'access-key': access_key, 'Content-Type': 'application/json'}
    logger.debug("headers is ----------------- %s", headers)

    timeout = httpx.Timeout(connect=30.0, read=60.0, write=10.0, pool=5.0)
    logger.debug("timeout is ----------------- %s", timeout)

    try:

        logger.debug("adminUrl is ----------------- %s", adminUrl)
        if adminUrl == None:
            raise HTTPException(status_code=400, detail="Environment variable ADMIN_URL is not set. Please add value to the ADMIN_URL environment variable")

        adminResponse = httpx.get(
            adminUrl+'/ava/force/workflow/payload',
            params=params, headers=headers, timeout=timeout
        )
        adminResponse.raise_for_status()

    except httpx.HTTPStatusError as e:
        logger.error("Admin api status error ----------------- %s", str(e))
        raise HTTPException(status_code=adminResponse.status_code, detail = str(e))
     
    except httpx.RequestError as e:
        logger.error("Admin api request error ----------------- %s", str(e))
        raise HTTPException(status_code=500, detail = str(e)) 

    logger.info("Admin pipeline payload response ----------------- %s", adminResponse.json())

    pipelineJson = adminResponse.json()

    if 'pipeline' not in pipelineJson:
        logger.info("Pipeline not found in the response")
        raise HTTPException(status_code=404, detail="Pipeline not found in the response")

    return pipelineJson

@app.post("/platform/pipeline/api/v1/execute")
async def execute(payload: PipelineModel):
    return await execute_pipeline(payload)

@app.post("/platform/pipeline/api/v1/execute/files")
async def execute(payload: str = Form(...), files: list[UploadFile] = None):
    print(f"Payload: {payload}")
    payload_dict = json.loads(payload)
    payloadObject = PipelineModel(**payload_dict)
    print(f"Payload: {payloadObject}")
    pipelineFiles = PipelineFiles()
    return await pipelineFiles.execute_pipeline_files(payload=payloadObject, files=files)

def setup_langfuse(payload):
    langfuse_metadata = {
        "trace_name": payload.name,  # set langfuse Trace Name
        "trace_id": payload.executionId,         # set langfuse Trace ID
        "trace_user_id": payload.user,       # set langfuse Trace User ID
        "tags": ["Workflow"]            # set langfuse Tags
    }
    return langfuse_metadata

# Tool instruction strings
TOOL_INSTRUCTIONS = {
        "FileWriterTool": "\n\nYou have access to the file_writer_tool. It is advised to use this tool when you have access to it irrespective of whether it's mentioned above to generate or create files explicitly.",
        "SerperDevTool": "\n\nYou have access to the SerperDevTool for web search. It is advised to use this tool when you have access to it irrespective of whether a web search task has been assigned explicitly.",
        "NL2SQLTool": "\n\nYou have access to the NL2SQLTool. It is advised to use this tool when you have access to it irrespective of whether a SQL task has been assigned explicitly.",
        "ScrapeWebsiteTool": "\n\nYou have access to the ScrapeWebsiteTool. It is advised to use this tool when you have access to it irrespective of whether a scraping task has been assigned explicitly.",
        "MemoryReaderWriterTool": "\n\nYou have access to the MemoryReaderWriterTool. It is advised to use this tool when you have access to it irrespective of whether a memory reading/writing task has been assigned explicitly.",
        "KnowledgeRAGTool": "\n\nYou have access to the KnowledgeRAGTool. It is advised to use this tool when you have access to it irrespective of whether a knowledge retrieval task has been assigned explicitly."
    }

async def setup_agents(agent: AgentDetails, userInputs:Dict[str,str], memory: bool, langfuse_config, executionId):
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
                        max_tokens=agent.llm.maxToken,
                        temperature=agent.llm.temperature,
                        top_p=agent.llm.topP,
                        metadata=langfuse_config,
                    )
            else:
                logger.debug("Bedrock Credentials are not used. %s", USE_BEDROCK_CREDENTIALS)
                llm = LLM(
                    model="bedrock/" + agent.llm.bedrockModelId,
                    aws_region_name=agent.llm.region,
                    max_tokens=agent.llm.maxToken,
                    temperature=agent.llm.temperature,
                    top_p=agent.llm.topP,
                    metadata=langfuse_config,
                )
        elif agent.llm.aiEngine == 'GoogleAI':
            logger.debug("Inside GoogleAI Block............")
            llm = LLM(
                model="vertex_ai/"+agent.llm.model,
                gcp_project_id=agent.llm.gcpProjectId,
                temperature=agent.llm.temperature,
                max_tokens=agent.llm.maxToken,
                location=agent.llm.gcpLocation,
                metadata=langfuse_config,
            )
        else:
            logger.error("Unsupported LLM type ----------------- %s", agent.llm.aiEngine)
            raise HTTPException(status_code=500, detail="Unsupported LLM type" + agent.llm.aiEngine)
        
        # Build common agent arguments
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
            "cache": False,
            "allow_code_execution": agent.allowCodeExecution,
            "code_execution_mode": "safe" if agent.isSafeCodeExecution else "unsafe"
        }
        
        # Optional fields
        print("Agent tools are ---------------- %s", agent.tools)
        
        if any(tool.toolName == 'MemoryReaderWriterTool' for tool in agent.tools):
            agent_args["step_callback"] = step_callback_fun

        # Add use_system_prompt only for certain LLMs
        if any(keyword in agent.llm.model for keyword in ["claude", "anthropic", "bedrock"]):
            agent_args["use_system_prompt"] = os.getenv("USE_SYSTEM_PROMPT", "true").lower() == "true"
        elif "o1" in agent.llm.model or "o3" in agent.llm.model:
            agent_args["use_system_prompt"] = False

        code_conversion_task = agent.task.description

        # Append tool instructions if the tool is present
        tool_names = [tool.toolName for tool in agent.tools]
        if "FileWriterTool" in tool_names:
            code_conversion_task += TOOL_INSTRUCTIONS["FileWriterTool"]
        if "SerperDevTool" in tool_names:
            code_conversion_task += TOOL_INSTRUCTIONS["SerperDevTool"]
        if "NL2SQLTool" in tool_names:
            code_conversion_task += TOOL_INSTRUCTIONS["NL2SQLTool"]
        if "ScrapeWebsiteTool" in tool_names:
            code_conversion_task += TOOL_INSTRUCTIONS["ScrapeWebsiteTool"]
        if "MemoryReaderWriterTool" in tool_names:
            code_conversion_task += TOOL_INSTRUCTIONS["MemoryReaderWriterTool"]

        for key, value in userInputs.items():
            
            code_conversion_task = code_conversion_task.replace(key, value)

    
        if has_image:
            toolbox.append(Imagetool(llm=llm))

        for tool in agent.tools:
            if tool.toolName == 'ScrapeWebsiteTool':
                scrapeWebsiteTool = None
                for param in tool.parameters:
                    if param.parameterName == "website_url" and param.value and param.value.strip():
                        scrapeWebsiteTool = ScrapeWebsiteTool(
                            website_url=param.value)
                
                if scrapeWebsiteTool == None:
                    PipelineAILogs().publishLogs("Website URL not provided for scrape website tool.", "red", redisClient=redis_client)
                    raise HTTPException(status_code=500, detail="Website URL not provided for scrape website tool.")
                
                logger.info("ScrapeWebsiteTool -------------------- %s", scrapeWebsiteTool)
                # agent_model.tools.append(scrapeWebsiteTool)
                toolbox.append(scrapeWebsiteTool)
                
            elif tool.toolName == 'MemoryReaderWriterTool':
                logger.info("MemoryReaderWriterTool being added to the agent")
                memReadWriteTool = MemoryReaderWriterTool(execution_id=executionId)
                # agent_model.tools.append(memReadWriteTool)
                toolbox.append(memReadWriteTool)
                
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

                # agent_model.tools.append(file_writer_tool)
        
            elif tool.toolName == 'NL2SQLTool':
                nl2sql_tool = None
                for param in tool.parameters:
                    if param.parameterName == "db_uri" and param.value and param.value.strip():
                        encoded_uri = encode_db_uri(param.value)
                        nl2sql_tool = SQLTool(db_uri=encoded_uri)
                if nl2sql_tool == None:
                    PipelineAILogs().publishLogs("Database URI not provided for NL2SQL tool.", "red", redisClient=redis_client)
                    raise HTTPException(status_code=500, detail="Database URI not provided for NL2SQL tool.")
          
                # agent_model.tools.append(nl2sql_tool)
                toolbox.append(nl2sql_tool)
            

        for tool in agent.userTools:
            tool_class_name = tool.toolClassName
            logger.debug("user tool class name ------------ %s ",tool_class_name)
            tool_class_definition = tool.toolClassDef
            logger.debug("user tool class def ------------ ")
            tool_instance = add_dynamic_user_tools(tool_class_name,tool_class_definition)
            logger.debug("user tool instance created")
            code_conversion_task += f"\n\nYou have access to the the tool '{tool_class_name}'. It is advised to use this tool when you have access to it irrespective of whether it has been asked to be used explicitly."
            # agent_model.tools.append(tool_instance)
            toolbox.append(tool_instance)

        if not agent.embedding == None:
            logger.debug("Agent embedding ------------ %s ", agent.embedding)
            code_conversion_task += TOOL_INSTRUCTIONS["KnowledgeRAGTool"]
            contextTool = KnowledgeRAGTool(input=code_conversion_task,
                                           agentEmbedding=agent.embedding,
                                           kwargs={"redis_client": redis_client})
            toolbox.append(contextTool)
            # agent_model.tools.append(contextTool)
        
        agent_args["tools"] = toolbox

        # Instantiate the agent
        agent_model = Agent(**agent_args)

        logger.debug(f"Setting up agent with userInput: {userInputs}")

        task = Task(
            description=code_conversion_task,
            expected_output=agent.task.expectedOutput,
            agent=agent_model
        )

        return agent_model, task

    except openai.BadRequestError as err:
        logger.error("OpenAI BadRequestError: Failed to create Agent - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: OpenAI BadRequestError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=400, detail=f"Bad request to OpenAI API: {str(err)}")

    except openai.AuthenticationError as err:
        logger.error("OpenAI AuthenticationError: Failed to authenticate - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: OpenAI AuthenticationError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=401, detail="Authentication failed with OpenAI API")

    except openai.APIConnectionError as err:
        logger.error("OpenAI APIConnectionError: Failed to connect to API - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: OpenAI APIConnectionError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=503, detail="Failed to connect to OpenAI API")

    except openai.RateLimitError as err:
        logger.error("OpenAI RateLimitError: Rate limit exceeded - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: OpenAI RateLimitError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=429, detail="OpenAI API rate limit exceeded")

    except ValueError as err:
        logger.error("ValueError: Invalid input or configuration - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: ValueError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=400, detail=f"Invalid input or configuration: {str(err)}")

    except KeyError as err:
        logger.error("KeyError: Missing required key - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: KeyError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=400, detail=f"Missing required configuration key: {str(err)}")

    except ImportError as err:
        logger.error("ImportError: Failed to import required module - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: ImportError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=500, detail=f"Failed to import required module: {str(err)}")

    except redis.RedisError as err:
        logger.error("RedisError: Failed to interact with Redis - %s", str(err))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: RedisError - {str(err)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=500, detail=f"Redis interaction failed: {str(err)}")

    except HTTPException as err:
        # Re-raise HTTP exceptions without modification
        raise

    except Exception as e:
        logger.error("Unexpected error: Failed to create Agent - %s", str(e))
        PipelineAILogs().publishLogs(f"DA Pipeline Exception: Unexpected error - {str(e)}", "red", redisClient=redis_client)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

async def execute_pipeline_logic(payload: PipelineModel, langfuse_config, access_key: str):
    try:
        agents = []
        tasks = []
        folder_path = os.path.join(os.getcwd(),payload.executionId)

        for agent_data in payload.pipeLineAgents:
            agent, task = await setup_agents(agent_data.agent, payload.userInputs, payload.enableAgenticMemory, langfuse_config, payload.executionId)
            agents.append(agent)
            tasks.append(task)

        manager_llm = None
        if payload.managerLlm:
            if payload.managerLlm.aiEngine == 'AmazonBedrock':
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
                            max_tokens = payload.managerLlm.maxToken,
                            temperature = payload.managerLlm.temperature,
                            top_p = payload.managerLlm.topP,
                            metadata = langfuse_config
                        )
                else:
                    logger.debug("Bedrock Credentials are not used. %s", USE_BEDROCK_CREDENTIALS)
                    manager_llm = LLM(
                        model="bedrock/" + payload.managerLlm.bedrockModelId,
                        aws_region_name=payload.managerLlm.region,
                        max_tokens = payload.managerLlm.maxToken,
                        temperature = payload.managerLlm.temperature,
                        top_p = payload.managerLlm.topP,
                        metadata = langfuse_config
                    )
            elif payload.managerLlm.aiEngine == 'AzureOpenAI':
                if "o1" in payload.managerLlm.model or "o3" in payload.managerLlm.model:
                    manager_llm = LLM(
                        model="azure/" + payload.managerLlm.llmDeploymentName,
                        base_url=payload.managerLlm.azureEndpoint,
                        api_key=payload.managerLlm.apiKey,
                        api_version=payload.managerLlm.llmApiVersion,
                        metadata = langfuse_config
                    )
                elif "deepseek" in payload.managerLlm.model.lower():
                    manager_llm = LLM(
                        model=payload.managerLlm.model,
                        temperature=payload.managerLlm.temperature,
                        max_tokens=payload.managerLlm.maxToken,
                        base_url=payload.managerLlm.azureEndpoint,
                        api_key=payload.managerLlm.apiKey,
                        metadata = langfuse_config
                    )
                else:
                    manager_llm = LLM(
                        model="azure/" + payload.managerLlm.llmDeploymentName,
                        temperature=payload.managerLlm.temperature,
                        max_tokens=payload.managerLlm.maxToken,
                        base_url=payload.managerLlm.azureEndpoint,
                        api_key=payload.managerLlm.apiKey,
                        api_version=payload.managerLlm.llmApiVersion,
                        metadata = langfuse_config
                    )
            elif payload.managerLlm.aiEngine == 'GoogleAI':
                logger.debug("Inside GoogleAI Block............")
                manager_llm = LLM(
                    model="vertex_ai/" + payload.managerLlm.model,
                    gcp_project_id=payload.managerLlm.gcpProjectId,
                    temperature=payload.managerLlm.temperature,
                    max_tokens=payload.managerLlm.maxToken,
                    location=payload.managerLlm.gcpLocation,
                    metadata = langfuse_config
                )
            else:
                raise ValueError("Unsupported LLM type for manager_llm")

        if manager_llm:
            logger.debug("manager llm values  %s", manager_llm)

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
                    use_system_prompt=False,
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

            logger.debug("manager llm values null Else block ---------->")
            
            crew = Crew(
                agents=agents,
                tasks=tasks,
                verbose=True,
                memory=payload.enableAgenticMemory,
                embedder=create_embedder(payload.masterEmbedding) if payload.enableAgenticMemory else None
            )

        crew_output = crew.kickoff()

        file_id = zip_and_upload_folder(pipelineId=payload.pipelineId,executionId=payload.executionId,user=payload.user,folder_path=folder_path,access_key=access_key)
        
        PipelineAILogs().publishLogs("DA Pipeline Logs Completed", "green",redisClient=redis_client)
        
        for agent in agents:
            if any(isinstance(tool, FileWriterTool) for tool in agent.tools):
                return crew_output, file_id
            else:
                continue

        return crew_output,"Not applicable"
    
    except OutputParserException as err:
        logger.error("Output Parser ----------------- %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=redis_client)
        raise HTTPException(status_code=500, detail="Failed to execute Pipeline: " + str(err))
    
    except ConnectionError as err:
        logger.error("Http ----------------- %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=redis_client)
        raise HTTPException(status_code=500, detail="Failed to execute Pipeline: " + str(err))
    
    except openai.BadRequestError as err:
        logger.error("Failed to execute Pipeline ----------------- %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=redis_client)
        raise HTTPException(status_code=500, detail="Failed to execute Pipeline: " + str(err))
    
    except litellm.BadRequestError as err:
        logger.error("Failed to execute Pipeline ----------------- %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=redis_client)
        raise HTTPException(status_code=500, detail="Failed to execute Pipeline files: " + str(err))

    except litellm.AuthenticationError as err:
        logger.error("Authentication failed: %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=redis_client)
        raise HTTPException(status_code=401, detail="Authentication failed: " + str(err))
    
    except openai.PermissionDeniedError as err:
        logger.error("Permission denied: %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=redis_client)
        raise HTTPException(status_code=403, detail="Permission denied: " + str(err))
    
    except litellm.NotFoundError as err:
        logger.error("Resource not found: %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=redis_client)
        raise HTTPException(status_code=404, detail="Resource not found: " + str(err))
    
    except litellm.RateLimitError as err:
        logger.error("Rate limit exceeded: %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=redis_client)
        raise HTTPException(status_code=429, detail="Rate limit exceeded: " + str(err))
    
    except litellm.APIConnectionError as err:
        logger.error("API connection error: %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception: " + str(err), "red", redisClient=redis_client)
        raise HTTPException(status_code=503, detail="API connection error: " + str(err))
    
    except Exception as err:
        logger.error("Failed to execute Pipeline ----------------- %s", str(err))
        PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(err), "red",redisClient=redis_client)
        raise HTTPException(status_code=500, detail="Failed to execute Pipeline: " + str(err))
    
    finally:

        logger.info("Deleting subfolder: %s", folder_path)

        # Ignore errors if folder doesn't exist
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=False, onerror=remove_readonly)
        except Exception as e:
            logger.error("Error Deleting generated file: %s", str(e))
            PipelineAILogs().publishLogs("DA Pipeline Exception:" + str(e), "red",redisClient=redis_client)


def add_dynamic_user_tools(class_name, class_definition):
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


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app=app, port=8081)