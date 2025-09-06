# Azure OpenAI RAG Chatbot 

An **HTTP-based chatbot** (with optional CLI) powered by **Azure OpenAI**, with:
- **Document Intelligence preprocessing** (`di_main.py`) → extracts text from raw PDFs/images and writes processed text to Blob
- **Portal-managed indexing & vectorization** in **Azure AI Search** (Import & vectorize data)
- **Hybrid retrieval** (BM25 + vector) with optional **Semantic re-ranking**
- **Grounded prompt** (relaxed) that allows discussion/analysis of the stories
- **Session persistence** in **Azure Cosmos DB**

> **Status:** Deployed on Azure Functions (Flex) and runnable locally.  
> For cloud tests use your Function URL. For local tests use `http://localhost:7071`.

---

## Features

- **Knowledge base:** documents ingested with **Document Intelligence** (`di_main.py`) and stored in Blob; indexed & vectorized using **Azure AI Search portal**
- **Retrieval:** Hybrid (BM25 + vector) with query rewriting for better follow-ups
- **Prompt:** relaxed grounding → interpretive/analytical questions about stories are answered (no “not in my expertise”)
- **Sessions:** stored in Cosmos; full UI controls (clear, restart, history, load session)

---

## Prerequisites

- Python **3.10+** and `pip`
- (For local HTTP) **Azure Functions Core Tools** (`func`)
- Node.js **18+** (for frontend)
- Azure resources:
  - **Azure OpenAI**
  - **Azure AI Search** (index + vectorization configured in portal)
  - **Azure Cosmos DB**
  - **Storage Account** (for raw + processed docs; required by Functions)
  - **Cognitive Services / Document Intelligence**

---

## Setup (local)

### 1) Create `.env` at repo root (Function App)

```ini
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>                     
AZURE_OPENAI_API_VERSION=<api-version>            
AZURE_OPENAI_DEPLOYMENT_NAME=<chat-deployment> 
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<embedding-deployment>

# Azure AI Search (KB)
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_INDEX=stories-index
AZURE_SEARCH_API_KEY=<your-search-query-key>
AZURE_SEARCH_SEMANTIC_CONFIG=<optional-semantic-config>

# Cosmos DB (session store)
COSMOS_URI=<your-cosmos-uri>
COSMOS_KEY=<your-cosmos-key>
COSMOS_DB=<your-db-name>
COSMOS_CONTAINER=<your-container-name>

# Document Intelligence (for di_main.py ingestion)
FORMREC_ENDPOINT=https://<your-di-resource>.cognitiveservices.azure.com/
FORMREC_KEY=<your-di-key>
BLOB_CONNECTION_STRING=<your-blob-connection>
RAW_CONTAINER=raw-docs
PROCESSED_CONTAINER=processed-docs
```

### 2) Install backend dependencies

```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3) Run Document Intelligence ingestion (once per new docs)

```bash
cd document_intelligence
python di_main.py
```

This extracts text from files in the raw Blob container and writes processed text to the processed Blob container, which the Azure AI Search portal indexer uses for *Import and vectorize data*.

### 4) Run the Function locally

Ensure `function_app/local.settings.json` mirrors your `.env`.

```bash
cd function_app
func start
```

Test with:

```bash
curl -X POST http://localhost:7071/api/chatbot_function \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me about the teacher"}'
```

---



## Deployment (Azure Functions)

### Publish backend:

```bash
cd function_app
func azure functionapp publish <your-function-app-name> --python
```

Then set all environment variables (OpenAI, Search, Cosmos, DI) in Function App → Configuration.


---

## Endpoint & API Usage

**Default route:**

```http
POST https://<APP>.azurewebsites.net/api/chatbot_function
```

**Payload:**

```json
{
  "message": "Tell me about the teacher",
  "session_id": "optional-uuid"
}
```

**Special commands:**
- `"history"` → returns saved turns for the current session
- `"clear"` → clears the current session
- `"restart"` → creates a new session and returns `new session_id`

---

## How it works (high-level)

### Document ingestion

- Run `di_main.py` → Document Intelligence extracts text from PDFs/images
- Outputs written to processed Blob container

### Knowledge base build (portal)

- Azure AI Search portal → Import and vectorize data from processed Blob
- Creates index with `text_vector` and metadata fields

### Runtime (chat)

- Session loaded from Cosmos
- Query rewritten to be self-contained
- Hybrid retrieval (BM25 + vector) from Search index
- Relaxed grounded prompt built with query + sources
- Azure OpenAI generates reply
- Conversation persisted in Cosmos

---



