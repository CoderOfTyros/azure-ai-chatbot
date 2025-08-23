# Azure OpenAI Chatbot

A minimal command-line chatbot and a local HTTP endpoint powered by Azure OpenAI.

> **Note:** I didn’t have time to deploy the Azure Function to Azure. I ran it **locally** instead, so POST requests to my **local machine endpoint** reach Azure OpenAI and return replies.

---

## Prerequisites
- Python 3.10+ and `pip`
- (For the local HTTP endpoint) **Azure Functions Core Tools** (`func` CLI)

## Setup

### 1) Secrets / config
Create a `.env` file at the project root with:
```ini
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>                       # or AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>  # exact Deployment Name
```
> Don’t commit real secrets. If keys slipped into history, rotate them in the Azure portal.

### 2) Install dependencies
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

---

## Run the CLI chatbot
```bash
# from repo root
python cli/main.py
```

You should see:
```
Welcome to your AI Chatbot! Write 'exit' or 'quit' to quit.
```
Type a message and press **Enter**. Exit with `exit` or `quit`.

---

## Run the local HTTP endpoint (Azure Functions)

1) Ensure **function_app/local.settings.json** has the same values as your `.env` (endpoint, key, API version, deployment name).

2) Install function dependencies:
```bash
pip install -r function_app/requirements.txt
```

### 3) Start the function locally
```bash
cd function_app
func start
```

### 4) Send a POST request to the local endpoint (default route)
```bash
curl -X POST http://localhost:7071/api/chatbot_function \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

**Expected response**
```json
{ "reply": "..." }
```

---

## Project structure
```
.
├─ .env
├─ requirements.txt
├─ cli/
│  ├─ main.py            # CLI entry point (welcome, input loop, graceful exit)
│  ├─ chatbot.py         # conversation logic, prints replies
│  └─ openai_client.py   # AzureOpenAI client init (loads .env)
└─ function_app/
   ├─ host.json
   ├─ local.settings.json
   └─ chatbot_function/
      ├─ function.json   # HTTP trigger (POST)
      ├─ __init__.py     # reads JSON {"message": "..."} and replies
      └─ openai_client.py
```

## Common issues
- **Deployment not found** → Ensure `AZURE_OPENAI_DEPLOYMENT_NAME` matches the *Deployment Name* in the Azure portal (not just the model name).
- **401 Unauthorized** → Check the endpoint and API key.
- **Local function route** → Default local route is `http://localhost:7071/api/chatbot_function` (HTTP **POST**).
