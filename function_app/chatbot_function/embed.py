import os
from .openai_client import init_openai_client



client, _ = init_openai_client()

embedding_model = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(model=embedding_model, input=[text])
    return response.data[0].embedding
