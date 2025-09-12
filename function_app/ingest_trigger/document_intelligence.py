import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.exceptions import HttpResponseError


document_intelligence_client = DocumentIntelligenceClient(
    endpoint=os.environ.get("DOCUMENTINTELLIGENCE_ENDPOINT"),
    credential=AzureKeyCredential(os.environ.get("DOCUMENTINTELLIGENCE_API_KEY"))
)

def extract_text_from_document(file_bytes: bytes, filename: str) -> str:
    try:
        poller = document_intelligence_client.begin_analyze_document(
            model_id="prebuilt-read",
            document=file_bytes
        )
        result = poller.result()

        lines = []
        for page in result.pages:
            for line in page.lines:
                lines.append(line.content)

        return "\n".join(lines)

    except HttpResponseError as e:
        raise RuntimeError(f"Document Intelligence failed: {e.message}")
