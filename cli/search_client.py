import os
from typing import Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

_search_client_singleton: Optional[SearchClient] = None

def get_search_client() -> SearchClient:
    global _search_client_singleton
    if _search_client_singleton:
        return _search_client_singleton

    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    index_name = os.environ.get("AZURE_SEARCH_INDEX")
    api_key = os.environ.get("AZURE_SEARCH_API_KEY", "")

    if not endpoint or not index_name:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_INDEX must be set")

    if api_key:
        cred = AzureKeyCredential(api_key)
    else:
        # Role-based access (AAD)
        cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)

    _search_client_singleton = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=cred,
    )
    return _search_client_singleton
