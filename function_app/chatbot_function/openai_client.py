# NOTE: This file is duplicated in both CLI and Function App for simplicity.

import os
from openai import AzureOpenAI

def init_openai_client():
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")


    if not all([endpoint, api_key, api_version, deployment_name]):
        raise ValueError("Missing one or more required environment variables.")
    

    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
    )

    return client, deployment_name
