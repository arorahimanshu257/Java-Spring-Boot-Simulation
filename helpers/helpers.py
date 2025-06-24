import boto3
import base64
import json
import httpx
from langchain_core.documents import Document
import os
import zipfile
import requests
from helpers.logger_config import logger
from PipelineModel.PipelineModel import PipelineModel
from crewai import LLM as BaseLLM

def decode_access_key(key):
    return base64.b64decode(key).decode("utf-8")

def create_embedder(payloadObject):
    embedder_config = {
        "AzureOpenAI": lambda: {
            "provider": "azure",
            "config": {
                "api_key": decode_access_key(payloadObject.embedding_api_key),
                "api_base": payloadObject.embedding_azure_endpoint,
                "api_version": payloadObject.embedding_api_version,
                "model": payloadObject.embedding_deployment_name,
            },
            "chromadb":{
                "chroma_end_point":payloadObject.chroma_end_point,
                "chroma_port":payloadObject.chroma_port,
            }
        },
        "AmazonBedrock": lambda: {
            "provider": "bedrock",
            "config": {
                "session": boto3.Session(
                    aws_access_key_id=decode_access_key(payloadObject.embedding_aws_key),
                    aws_secret_access_key=decode_access_key(payloadObject.embedding_aws_secret_key),
                    region_name=payloadObject.embedding_aws_region
                )
            },
            "chromadb":{
                "chroma_end_point":payloadObject.chroma_end_point,
                "chroma_port":payloadObject.chroma_port,
            }
        }
    }
    
    # Fetch the embedder configuration based on payloadObject.type
    embedder = embedder_config.get(payloadObject.aiEngine, lambda: None)()
    if embedder is None:
        raise ValueError(f"Unsupported embedder type: {payloadObject.aiEngine}")
    return embedder


def parent_doc_retriever(docs):

    matching_documents = []

    text_list = []
    
    child_chunks = docs

    for chunk in child_chunks:

        metadata = json.loads(chunk.metadata["parent_metadata"])

        if chunk.metadata["parent_text"] not in text_list:
            
            matching_documents.append(Document(page_content=chunk.metadata["parent_text"], metadata=metadata))
            
            text_list.append(chunk.metadata["parent_text"])

    return matching_documents

def save_initial_workflow_history(pipelineId, executionId, user, md_requests, adminUrl, access_key):
    try:
        data = {
            "pipelineId": pipelineId,
            "executionId": executionId,
            "record": {
                "user": user,
                "request": json.dumps(md_requests)
            }
        }
        response = httpx.post(adminUrl + '/ava/force/workflow/history', headers=get_headers(access_key), json=data)
        logger.info(f"save initial workflow history response : {response}")
    except Exception as e:
        logger.error(f"Error in save_initial_workflow_history: {e}")

def save_payload_workflow_history(pipelineId, executionId, fullpayload, adminUrl, access_key):
    try:
        data = {
            "pipelineId": pipelineId,
            "executionId": executionId,
            "record": {
                "full_payload": json.dumps(fullpayload)
            }
        }
        response = httpx.post(adminUrl + '/ava/force/workflow/history', headers=get_headers(access_key), json=data)
        logger.info(f"save full payload workflow history response : {response}")
    except Exception as e:
        logger.error(f"Error in save_payload_workflow_history: {e}")

def mask_value(value):
    return '#' * len(value)

def mask_response(response: PipelineModel):

    def mask_if_exists(obj, attr):
        if getattr(obj, attr):
            setattr(obj, attr, mask_value(getattr(obj, attr)))

    if response.masterEmbedding:
        mask_if_exists(response.masterEmbedding, 'embedding_api_key')
        mask_if_exists(response.masterEmbedding, 'embedding_aws_secret_key')
        mask_if_exists(response.masterEmbedding, 'embedding_aws_key')
        mask_if_exists(response.masterEmbedding, 'embedding_gcp_project_id')

    if response.managerLlm:
        mask_if_exists(response.managerLlm, 'apiKey')
        mask_if_exists(response.managerLlm, 'accessKey')
        mask_if_exists(response.managerLlm, 'secretKey')
        mask_if_exists(response.managerLlm, 'gcpProjectId')

    for agent in response.pipeLineAgents:
        if agent.agent.llm:
            mask_if_exists(agent.agent.llm, 'apiKey')
            mask_if_exists(agent.agent.llm, 'accessKey')
            mask_if_exists(agent.agent.llm, 'secretKey')
            mask_if_exists(agent.agent.llm, 'gcpProjectId')
        if agent.agent.embedding:
            for embedding in agent.agent.embedding:
                mask_if_exists(embedding, 'embedding_api_key')
                mask_if_exists(embedding, 'embedding_aws_secret_key')
                mask_if_exists(embedding, 'embedding_aws_key')
                mask_if_exists(embedding, 'embedding_gcp_project_id')
        
        mask_if_exists(response.langfuse,'langfusePublicKey')
        mask_if_exists(response.langfuse,'langfuseSecretKey')


    return response


def save_final_workflow_history(pipelineId, executionId, crew_output, finalResponse, adminUrl, access_key,upload_file_id):
    try:

        masked_response = mask_response(finalResponse)


        data = {
            "pipelineId": pipelineId,
            "executionId": executionId,
            "record": {
                "response": masked_response.model_dump_json() ,
                "total_tokens": crew_output[0].token_usage.total_tokens,
                "prompt_tokens": crew_output[0].token_usage.prompt_tokens,
                "cached_prompt_tokens": crew_output[0].token_usage.cached_prompt_tokens,
                "completion_tokens": crew_output[0].token_usage.completion_tokens,
                "successful_requests": crew_output[0].token_usage.successful_requests,
                "upload_file_id": upload_file_id
            }
        }
    
        response = httpx.post(adminUrl + '/ava/force/workflow/history', headers=get_headers(access_key), json=data)
        
        logger.info(f"save final workflow history response : {response}")
    
    except Exception as e:
        logger.error(f"Error in save_final_workflow_history: {e}")



def get_headers(access_key):
    return {
        "Content-Type": "application/json",
        "access-key": access_key
    }


def zip_and_upload_folder(pipelineId, executionId, user, folder_path, access_key):
    
    if not os.path.exists(folder_path):

        return ""

    upload_url = f"{os.environ['ADMIN_URL']}/ava/force/workflow/history/upload-file"

    zip_filename = f'{executionId}.zip'
    
    try:
        # Create a zip file containing the folder contents
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)

        
        # Define the file and form data
        with open(f"{zip_filename}", "rb") as file:

            files = {"file": (f"{zip_filename}", file, "application/zip")}

            data = {
            'executionId': str(executionId),
            'pipelineId': str(pipelineId),
            'user': str(user)}

            headers = {"access-Key":str(access_key)}

            # Upload the zip file to the endpoint
            response = requests.post(upload_url, files=files, data=data, headers=headers)

        # Check if the request was successful
        if response.status_code == 201:
            file_id = response.json()
            return str(file_id)
        else:
            raise Exception(f"File Upload failed with status code: {response.status_code}, reason: {response.reason}")

    except Exception as e:
        logger.error(f"Exception while trying to create zip file : {e}")
        return None

    finally:
        # Clean up the temporary zip file
        if os.path.exists(zip_filename):
            os.remove(zip_filename)

def send_execution_status(execution_id: str, status: str, instructionUrl: str, access_key: str):
    try:
        status_url = f"{instructionUrl}/ava/force/workflow-executions/{execution_id}/status"
        
        data = {
            "status": status
        }
        response = httpx.post(status_url, headers=get_headers(access_key), json=data)

        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending execution status for execution_id {execution_id}: {e}")
        return False

class PatchedBedrockLLM(BaseLLM):
    def call(self, prompt: str, **kwargs):
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            flattened_content = "\n\n".join(
                f"{msg.get('content', '')}" for msg in prompt
            )
            messages = [{"role": "user", "content": flattened_content}]
        else:
            raise ValueError("Invalid prompt format passed to Bedrock model")
        kwargs.pop("prompt", None)
        kwargs["messages"] = messages
        return super().call(**kwargs)