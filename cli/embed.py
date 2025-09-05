import os
from dotenv import load_dotenv
from .openai_client import init_openai_client

load_dotenv()

client, _ = init_openai_client()

embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

def embed_one(text: str) -> list[float]:
    response = client.embeddings.create(model=embedding_model, input=[text])
    return response.data[0].embedding
