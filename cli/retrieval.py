from typing import List, Dict, Any, Optional
from azure.search.documents.models import VectorizedQuery
from .search_client import get_search_client
from .embed import embed_text  

# Fields in the RAG index 
RAG_SELECT = "title,chunk,parent_id,chunk_id"
RAG_VECTOR_FIELD = "text_vector"  # embedding field in the index

def search_top_k_hybrid(query: str, k: int = 5, semantic_config: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval against the RAG index: BM25 over 'chunk' + vector over 'text_vector'.
    Returns: [{ title, content, raw }]
    """
    client = get_search_client()
    vec = embed_text(query)

    vq = VectorizedQuery(
        vector=vec,
        k_nearest_neighbors=k,   
        fields=RAG_VECTOR_FIELD
    )

    kwargs = dict(
        search_text=query,  # keyword/BM25 (and semantic if configured)
        vector_queries=[vq],
        select=RAG_SELECT,
        top=k,
    )
    if semantic_config:
        kwargs.update(query_type="semantic", semantic_configuration_name=semantic_config)

    try:
        results = client.search(**kwargs)
    except Exception:
        # Fallback to keyword-only if vector fails (quota, field mismatch, etc.)
        results = client.search(search_text=query, select=RAG_SELECT, top=k)

    passages: List[Dict[str, Any]] = []
    for doc in results:
        title = str(doc.get("title") or "")
        content = str(doc.get("chunk") or "")
        passages.append({
            "title": title.strip(),
            "content": content.strip(),
            "raw": doc
        })
    return passages

def format_sources_for_prompt(passages: List[Dict[str, Any]]) -> str:
    lines = []
    for p in passages:
        lines.append(f'{p["title"]}:{p["content"]}:')  
    return "\n".join(lines)
