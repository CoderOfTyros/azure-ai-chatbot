from typing import List, Dict, Any
from .search_client import get_search_client

DEFAULT_SELECT = "HotelName,Description,Tags"  

def search_top_k(query: str, k: int = 5, select: str = None) -> List[Dict[str, Any]]:
    """
    Runs a classic BM25 search against Azure AI Search and returns normalized passages.
    Returns: [{ title, content, tags, raw }]
    """
    client = get_search_client()
    fields = select or DEFAULT_SELECT

   
    results = client.search(
        search_text=query,
        top=k,
        select=fields
    )

    passages: List[Dict[str, Any]] = []
    for doc in results:
        title = str(doc.get("HotelName") or doc.get("title") or "")
        content = str(doc.get("Description") or doc.get("content") or "")
        tags = doc.get("Tags") or doc.get("tags") or []
        passages.append({
            "title": title.strip(),
            "content": content.strip(),
            "tags": tags,
            "raw": doc
        })
    return passages

def format_sources_for_prompt(passages: List[Dict[str, Any]]) -> str:
    """
    Matches the quickstart style: 'HotelName:Description:Tags'.
    """
    lines = []
    for p in passages:
        tags = ", ".join(p["tags"]) if isinstance(p["tags"], (list, tuple)) else str(p["tags"])
        lines.append(f'{p["title"]}:{p["content"]}:{tags}')
    return "\n".join(lines)
