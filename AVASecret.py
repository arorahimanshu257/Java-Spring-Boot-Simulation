import requests
from helpers.secret_manager import secret_manager
import json
from helpers.logger_config import logger
from fastapi import HTTPException
import os

# os.environ["SECRETS_URL"] ="https://avaplus-dev.avateam.io/v1/api/secrets/ava/force/da/secret"

def getValue(secret_key):
    url = os.getenv("SECRETS_URL")
    params = {"secret-key": secret_key}
    headers = {"access-key": secret_manager.access_key}

    try:

        response = requests.get(url, params=params, headers=headers)

        response.raise_for_status()
        
        response_dict = json.loads(response.text)

        return response_dict[secret_key]
    
    except requests.RequestException as e:
        logger.error(f"Error occurred while fetching API key: {e}")
        raise HTTPException(status_code=400, detail=f"Error occurred while fetching API key: {e}")