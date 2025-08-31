# Azure OpenAI Chatbot 

A **command-line** chatbot and an **HTTP endpoint** powered by **Azure OpenAI**, with:
- **RAG** (Retrieval-Augmented Generation) using **Azure AI Search** as the **knowledge base**
- **Session persistence** in **Azure Cosmos DB**
- Works **locally** and **on Azure Functions (Flex Consumption)**

> **Status:** Deployed on Azure Functions and runnable locally.  
> For cloud tests use your Function URL. For local tests use `http://localhost:7071`.

---

## What’s new in Lab 3
- **Knowledge Base:** Azure AI Search index (`hotels-sample-index` from the tutorial)  
- **Retrieval:** BM25 (For Free tier)  
- **Grounded Prompt:** Answer from sources when relevant; otherwise use general knowledge  
- **Sessions:** Stored in Cosmos DB so `clear`, `history`, and `restart` work across runs

---

## Prerequisites
- Python **3.10+** and `pip`
- (For local HTTP) **Azure Functions Core Tools** (`func`)
- Azure resources:
  - **Azure OpenAI**
  - **Azure AI Search** (service with the **hotels** sample index)
  - **Azure Cosmos DB**
  - **Storage Account** (used by Azure Functions)

---

## Setup (local)

### 1) Create `.env` at repo root

```ini
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>                     
AZURE_OPENAI_API_VERSION=<model-api-version>            
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment> 

# Azure AI Search (KB)
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_INDEX=hotels-sample-index
AZURE_SEARCH_API_KEY=<your-search-query-key>    # easiest for local dev
# (If using RBAC instead of key locally, omit AZURE_SEARCH_API_KEY)

# Cosmos DB (session store)
COSMOS_URI=<your-cosmos-uri>
COSMOS_KEY=<your-cosmos-key>
COSMOS_DB=<your-db-name>
COSMOS_CONTAINER=<your-container-name>
```

Keep real keys out of git. Rotate if exposed.

### 2) Install dependencies

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Create the tutorial knowledge base (once)

Azure Portal → your Search service → Import data → Samples → choose hotels → Next/Finish.  
The index will be named `hotels-sample-index`.

(Optional on Basic+ tiers) Add a semantic config named `semantic-config` to the index JSON.  
On Free tier, semantic ranker isn’t available; BM25 works fine.

---

## Run the CLI chatbot (local)

```bash
# from outside repo root
python -m azure_ai_chatbot.cli.main.py
```

You’ll see:

```
Welcome to your AI Chatbot! Type 'exit', 'clear', 'restart', or 'history'.
Type questions like: Recommend hotels with complimentary breakfast.
```

---

## Run the HTTP endpoint locally (Azure Functions)

Ensure `function_app/local.settings.json` mirrors your `.env` (OpenAI/Search/Cosmos).

Install function deps:

```bash
pip install -r function_app/requirements.txt
```

Start:

```bash
cd function_app
func start
```

Test (both examples work):

```bash
## Postman

To test using **Postman**:

1. Open **Postman** and create a new request.
2. Set the method to **POST** and the URL to: http://localhost:7071/api/chatbot_function

3. Go to the **Body** tab → select **raw** → choose **JSON** from the dropdown.
4. Paste this JSON payload:

```json
{
  "message": "Recommend hotels with complimentary breakfast",
  "session_id": "", # Will create a new session
  "role": "hotel advisor"
}

# PowerShell
Invoke-RestMethod -Method POST "http://localhost:7071/api/chatbot_function" `
  -ContentType "application/json" `
  -Body '{"message":"hello"}'
```

---

## Cloud (Azure Functions) deployment & test

### Required App settings (Portal → Function App → Configuration)


#### Azure OpenAI

```
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_VERSION
AZURE_OPENAI_DEPLOYMENT_NAME
AZURE_OPENAI_KEY (if not using AAD)
```

#### Azure AI Search 

```
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_INDEX = hotels-sample-index
```

Either `AZURE_SEARCH_API_KEY` (recommended to verify quickly)  
or enable Managed Identity on the Function App and assign the Search service role  
(Search Index Data Reader / Contributor) to that identity.

#### Cosmos DB

```
COSMOS_URI
COSMOS_KEY
```

---

## Deploy (VS Code)

Open the project (repo root or `function_app/`).

VS Code Azure Functions extension → Sign in.  
Command Palette → `Azure Functions: Deploy to Function App` → select your app.

---

## Endpoint & test

Default route (no custom route):

```
POST https://<APP>.azurewebsites.net/api/chatbot_function
```


PowerShell one-liner:

```powershell
curl -Method POST "https://<APP>.azurewebsites.net/api/chatbot_function" `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"message":"hello","session_id":"test-1","role":"hotel advisor"}'
```

---

## How it works (high-level)

- Session load from Cosmos (by `session_id`)
- Retrieve top-k docs from Azure AI Search (`hotels-sample-index`) via BM25
- Grounded prompt built with Query + Sources
- Chat completion (Azure OpenAI) with low temperature (e.g., 0.3)
- Persist updated messages to Cosmos and return the reply

**RAG rule:**  
If sources clearly answer the query, the model answers only from them (and may list `Sources: …`).  
If not, it uses general knowledge *without fabricating citations*.

---

## Project structure

```
.
├─ README.md
├─ requirements.txt
├─ .env
├─ cli/
│  ├─ main.py                 # CLI entry (welcome, input loop)
│  ├─ chatbot.py              # conversation loop (RAG + OpenAI + Cosmos)
│  ├─ openai_client.py        # Azure OpenAI client init
│  ├─ retrieval.py            # BM25 search (top-k) + source formatting
│  ├─ search_client.py        # builds SearchClient (key or RBAC)
│  └─ prompts.py              # grounded prompt helper
└─ function_app/
   ├─ host.json
   ├─ local.settings.json
   ├─ requirements.txt 
   └─ chatbot_function/
      ├─ function.json        # HTTP trigger (POST); default route /api/chatbot_function
      ├─ __init__.py          # RAG flow + sessions + chat completion
      ├─ openai_client.py
      ├─ cosmos_session_manager.py
      ├─ utils.py             # summarize / trim helpers
      ├─ retrieval.py         # BM25 search (same as CLI)
      ├─ search_client.py
      └─ prompts.py
```

---


