# Azure OpenAI Chatbot

A minimal command-line chatbot and an HTTP endpoint powered by Azure OpenAI.

> **Status:** Deployed on **Azure Functions** and runnable **locally**. Use the **Function URL** in the portal for cloud tests, or `http://localhost:7071` for local tests.

---

## Prerequisites
- Python 3.10+ and `pip`
- (For local HTTP endpoint) **Azure Functions Core Tools** (`func`)

## Setup (local)

### 1) Secrets / config
Create a `.env` at the project root:
```ini
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>                       # or AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>  # exact Deployment Name
```
> Keep real keys out of git. Rotate keys if they’re ever exposed.

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

## Run the CLI chatbot (local)
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

## Run the HTTP endpoint locally (Functions)
1) Ensure `function_app/local.settings.json` mirrors your `.env` values (endpoint, key, version, deployment name).  
2) Install function deps:
```bash
pip install -r function_app/requirements.txt
```
3) Start:
```bash
cd function_app
func start
```
4) Test:
```bash
curl -X POST http://localhost:7071/api/chatbot_function \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```
Expected:
```json
{ "reply": "..." }
```

---

## Cloud (Azure Functions) deployment & test

### App settings (Portal → Function App → Configuration)
Set these **Application settings**:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY` (or `AZURE_OPENAI_KEY`)
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT_NAME`


### Deploy via VS Code (auto-zip)
1) Open the project in **VS Code** (you can open the repo root or just `function_app/`).  
2) Install the **Azure Functions** extension and **sign in** to Azure.  
3) **Command Palette → “Azure Functions: Deploy to Function App”**.  
4) Select your subscription → choose the **existing Function App** → confirm deploy.  
   > VS Code **builds and zips automatically** and uploads the package.

### Get the URL & test
Portal → Function App → **function Name** → `chatbot_function` → **add /api/function_name to domain name**.


**Postman:**
- POST `https://<APP_NAME>.azurewebsites.net/api/chatbot_function`
- Body → raw JSON:
```json
{ "message": "Hello!" }
```

---

## Project structure
```
.
├─ .env
├─ requirements.txt
├─ cli/
│  ├─ main.py            # CLI entry (welcome, input loop, graceful exit)
│  ├─ chatbot.py         # conversation logic
│  └─ openai_client.py   # AzureOpenAI client init (reads env)
└─ function_app/
   ├─ host.json
   ├─ local.settings.json
   └─ chatbot_function/
      ├─ function.json   # HTTP trigger (POST)
      ├─ __init__.py     # reads {"message": "..."} and replies
      └─ openai_client.py
```

