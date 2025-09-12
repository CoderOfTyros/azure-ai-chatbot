#!/usr/bin/env python3
"""
Create/Update a RAG-friendly Azure AI Search index (SDK 11.5.x)
- Loads .env (AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY, AZURE_SEARCH_INDEX_NAME)
- Uses HNSW vector search profile
- Declares vector field via SearchField with vector_search_dimensions + vector_search_profile_name
"""

import os
from dotenv import load_dotenv
from azure.search.documents import __version__ as azsearch_version
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,               # <-- use for the vector field
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,  # <-- correct class name in 11.5.x
    VectorSearchProfile,
)

# --- Load .env from this script's folder ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

endpoint   = os.getenv("AZURE_SEARCH_ENDPOINT")
admin_key  = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME") or os.getenv("AZURE_SEARCH_INDEX")

print("azure-search-documents version:", azsearch_version)
print("endpoint:", endpoint)
print("admin_key:", "SET" if admin_key else "MISSING")
print("index_name:", index_name)

if not endpoint or not admin_key or not index_name:
    print("❌ Missing environment variables. Check .env (ENDPOINT / ADMIN_KEY or API_KEY / INDEX_NAME or INDEX).")
    raise SystemExit(1)

client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))

# --- Fields ---
# Use SearchField for the vector field so vector props serialize correctly on 11.5.x
fields = [
    SimpleField(name="id",        type=SearchFieldDataType.String, key=True, filterable=True),
    SimpleField(name="fileId",    type=SearchFieldDataType.String, filterable=True, sortable=True),
    SearchableField(name="fileName", type=SearchFieldDataType.String, sortable=True),
    SearchableField(name="title",    type=SearchFieldDataType.String, sortable=True),
    SearchableField(name="chunk",    type=SearchFieldDataType.String),

    SimpleField(name="chunkId",   type=SearchFieldDataType.Int32,  filterable=True, sortable=True),

    # ---- Vector field (MUST be searchable=True; set dimensions + profile) ----
    SearchField(
        name="contentVector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,                       # required for vector fields
        vector_search_dimensions=1536,         # match your embedding model
        vector_search_profile_name="my-profile"
        # Optionals you may add:
        # stored=False,                         # don't store a copy for retrieval
        # hidden=True,                          # don't return vector in results
    ),

    SimpleField(name="source",    type=SearchFieldDataType.String, filterable=True, sortable=True),
    SimpleField(name="language",  type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="createdAt", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
]

# --- Vector search config (HNSW) ---
vector_search = VectorSearch(
    algorithms=[
        HnswAlgorithmConfiguration(
            name="my-hnsw"
            # You can optionally pass parameters via HnswParameters in newer SDKs.
            # In 11.5.x, name alone is enough to create a default HNSW config. :contentReference[oaicite:2]{index=2}
        )
    ],
    profiles=[
        VectorSearchProfile(
            name="my-profile",
            algorithm_configuration_name="my-hnsw",  # tie the field to this algorithm
        )
    ],
)

# --- Create or update index ---
index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search,
)

result = client.create_or_update_index(index)
print(f"✅ Index '{result.name}' created/updated successfully.")
