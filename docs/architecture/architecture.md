# Architecture

This documents the current basic chatbot architecture and data flow.

![Architecture Diagram](./diagram.png)

## Azure Resources
- **Resource Group:** `<your-resource-group>`
- **Azure OpenAI resource:** `<your-openai-resource>` (region `<region>`), deployment name: `<deployment-name>`

## Components
- **CLI App (`cli/main.py`)** — welcome message, input loop, graceful exit.
- **Chat Core (`cli/chatbot.py`, `cli/openai_client.py`)** — client initialization, message handling, response generation, error handling.
- **Local HTTP Function (`function_app/chatbot_function/`)** — runs locally; accepts `POST /api/chatbot_function` with body `{ "message": "..." }` and returns `{ "reply": "..." }`.

## Data Flow
1. User types a message in the terminal (or sends a POST to the local HTTP endpoint).
2. Application appends the user message to a rolling `messages` list and calls **Azure OpenAI** using the configured **deployment name**.
3. Azure OpenAI returns a completion (assistant content).
4. Application prints the reply and appends it to conversation state.

## Design Decisions
- Clear separation of concerns (CLI vs. chat core).
- Configuration via `.env` (endpoint, key, API version, deployment name).
- Maintains a simple in-memory conversation history.
- Basic error handling for API/network/unexpected errors.

> This diagram will be updated in future iterations as new features are added.