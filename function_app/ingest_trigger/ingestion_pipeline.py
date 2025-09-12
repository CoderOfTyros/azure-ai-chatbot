# function_app/ingest_trigger/ingestion_pipeline.py

from __future__ import annotations

from typing import List, Dict
from datetime import datetime

import tiktoken

from ..chatbot_function.embed import embed_text
from ..chatbot_function.search_client import get_search_client
from ..chatbot_function.utils import clean_text


def _get_encoder(encoding_name: str = "cl100k_base"):
    return tiktoken.get_encoding(encoding_name)

def _split_text_into_chunks(
    text: str,
    max_tokens: int = 300,
    overlap: int = 60,
    encoding_name: str = "cl100k_base",
) -> List[str]:
    enc = _get_encoder(encoding_name)
    tokens = enc.encode(text)
    n = len(tokens)
    if n == 0:
        return []

    chunks: List[str] = []
    start = 0
    step = max_tokens - overlap if max_tokens > overlap else max_tokens

    while start < n:
        end = min(start + max_tokens, n)
        chunk = enc.decode(tokens[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start += step

    return chunks

def upload_documents_to_search(documents: List[Dict]):
    client = get_search_client()
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        client.upload_documents(batch)

def process_and_index_text(text: str, filename: str, *, title: str = "", language: str = "en",max_tokens_per_chunk: int = 300,
    chunk_overlap: int = 60, encoding_name: str = "cl100k_base",):

    cleaned = clean_text(text)
    if not cleaned:
        return

    chunks = _split_text_into_chunks(
        cleaned,
        max_tokens=max_tokens_per_chunk,
        overlap=chunk_overlap,
        encoding_name=encoding_name,
    )
    if not chunks:
        return

    docs: List[Dict] = []
    file_id = filename.rsplit(".", 1)[0]  # remove extension
    created_at = datetime.utcnow().isoformat() + "Z"

    for i, chunk in enumerate(chunks, start=1):
        emb = embed_text(chunk)

        doc = {
            "id": f"{file_id}-chunk-{str(i).zfill(4)}",
            "fileId": file_id,
            "fileName": filename,
            "title": title or file_id,
            "chunk": chunk,
            "chunkId": i,
            "contentVector": emb,
            "source": "uploaded",
            "language": language,
            "createdAt": created_at,
        }
        docs.append(doc)

    upload_documents_to_search(docs)
