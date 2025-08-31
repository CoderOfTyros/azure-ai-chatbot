# Architecture 

This document outlines the architecture and data flow for the deployed Azure-based AI chatbot solution.

![Architecture Diagram](./architecture-v1.1.png)

## Azure Resources
- **Resource Group:** `<your-resource-group>`
- **Function App:** `<your-function-app>` (Python, HTTP trigger; Flex Consumption)
- **Storage Account:** `<your-storage>` (required by Functions)
- **Azure OpenAI:** `<your-openai-resource>` (region `<region>`, deployment: `<deployment-name>`)
- **Azure AI Search:** `<your-search-service>` — index: `hotels-sample-index` (tutorial KB)
- **Azure Cosmos DB:** `<your-cosmos-account>` — DB: `<db>` / Container: `<container>`
- *(Optional)* **Managed Identity** for Function App (if using RBAC instead of keys)

## Components
- **CLI App (`cli/main.py`, `cli/chatbot.py`)**
  - Interactive console; supports `clear`, `history`, `restart`.
  - Uses the same RAG pipeline as the Function.
- **HTTP Function (`function_app/chatbot_function/`)**
  - Endpoint: `POST /api/chatbot_function` (or custom route if set).
  - Body: `{"message": "...", "session_id": "...", "role": "..."}`.
  - Returns: `{"reply": "...", "session_id": "..."}`.
- **Chat Core / Utilities**
  - `openai_client.py` — initializes Azure OpenAI client.
  - `cosmos_session_manager.py` — loads/saves/clears conversation by `session_id`.
  - `utils.py` — summarization & token trimming.
- **RAG Layer**
  - `search_client.py` — builds `SearchClient` (API key or RBAC).
  - `retrieval.py` — BM25 search (Free tier), formats sources.
  - `prompts.py` — grounded prompt template (use sources if relevant; otherwise general knowledge).

## Data Flow
1. **Request in** (CLI input or HTTP POST).
2. **Session load** from Cosmos DB by `session_id`.
3. **RAG retrieval**  
   - Call Azure AI Search on `hotels-sample-index` with the user query (BM25).
   - Get top-k docs (`HotelName`, `Description`, `Tags`), format into “Sources”.
4. **Prompt assembly**  
   - System message sets persona (e.g., “You are a helpful *hotel advisor*.”).
   - Grounded user message includes: **Query** + **Sources** and decision rule:
     - If sources are relevant → answer **only** from them and add `Sources:` line.
     - If not sufficient → answer with **general knowledge** (no fake citations).
5. **Chat completion** via Azure OpenAI (temperature ~0.2–0.3 for grounded replies).
6. **Persist** updated conversation (excluding the system message) back to Cosmos.
7. **Response out**: JSON with `reply` (and optionally source titles if you expose them).

## Endpoint
- Default route:
  - `POST https://<app>.azurewebsites.net/api/chatbot_function`
- **Headers:** `Content-Type: application/json`

## Configuration (App Settings)
- **Azure OpenAI:**  
  `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_KEY` (if not AAD)
- **Azure AI Search (KB):**  
  `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX` (e.g., `hotels-sample-index`),  
  *Either* `AZURE_SEARCH_API_KEY` **or** Managed Identity with **Search Index Data Reader/Contributor**
- **Cosmos DB (sessions):**  
  `COSMOS_URI`, `COSMOS_KEY`, `COSMOS_DB`, `COSMOS_CONTAINER`


## Design Decisions
- **Knowledge base = Azure AI Search index** (tutorial hotels sample). No vectors or Semantic Ranker needed on Free tier.
- **Strict grounding** when sources are relevant; otherwise **fallback** to general knowledge per prompt instruction.
- **Session persistence** in Cosmos DB (supports `clear`, `history`, `restart`).
- **Shared logic** between Function and CLI to avoid code drift.


