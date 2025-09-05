import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

def get_di_client() -> DocumentAnalysisClient:
    endpoint = os.environ["DOCUMENT_INTELLIGENCE_ENDPOINT"]
    key = os.environ["DOCUMENT_INTELLIGENCE_KEY"]
    return DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

def extract_text_bytes(di: DocumentAnalysisClient, data: bytes, content_type: str | None) -> str:
    """
    Uses prebuilt-read to extract printed + handwritten text.
    """
    poller = di.begin_analyze_document(
        model_id="prebuilt-read",
        document=data,
        content_type=content_type
    )
    result = poller.result()
    if getattr(result, "content", None):
        return result.content
    lines = []
    for p in (result.pages or []):
        for ln in (p.lines or []):
            lines.append(ln.content)
    return "\n".join(lines)
