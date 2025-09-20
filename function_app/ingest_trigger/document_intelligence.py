import os
import io
from PIL import Image
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.ai.formrecognizer import DocumentAnalysisClient


_endpoint = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT")
_key = os.environ.get("DOCUMENT_INTELLIGENCE_KEY")

if not _endpoint or not _key:
    raise RuntimeError(
        "Missing Document Intelligence settings.\n"
        "Set DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY in your environment."
    )

# Normalize endpoint (avoid double slashes)
_endpoint = _endpoint.rstrip("/")


document_analysis_client = DocumentAnalysisClient(
    endpoint=_endpoint,
    credential=AzureKeyCredential(_key),
)


def _normalize_image_bytes(name: str, data: bytes) -> bytes:
    """
    Best-effort: open image bytes and re-encode as clean RGB PNG.
    Fixes cases where the extension is PNG but the actual encoding is WebP/HEIC/etc.,
    or where alpha/ICC profiles cause issues.
    """
    with Image.open(io.BytesIO(data)) as im:
        # Convert to a safe mode (RGB)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="PNG")  
        return out.getvalue()



def extract_text_from_document(file_bytes: bytes, filename: str = None) -> str:
    """
    Analyze a document using the prebuilt-read model (Form Recognizer v3)
    and return extracted text. For .txt files, decode directly.

    Args:
        file_bytes (bytes): File content in bytes (from blob trigger input).
        filename (str, optional): File name for logging/debugging.

    Returns:
        str: Extracted text from the document.
    """
    def _analyze(data: bytes) -> str:
        poller = document_analysis_client.begin_analyze_document(
            model_id="prebuilt-read",
            document=data,
        )
        result = poller.result()

        if getattr(result, "content", None):
            return result.content

        lines = []
        for page in getattr(result, "pages", []) or []:
            for line in getattr(page, "lines", []) or []:
                if line.content:
                    lines.append(line.content)
        return "\n".join(lines)

    # --- Case 1: plain text files ---
    ext = (os.path.splitext(filename or "")[1] or "").lower()
    if ext == ".txt":
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="replace")

    # --- Case 2: PDF, images, etc. via Form Recognizer ---
    try:
        return _analyze(file_bytes)

    except HttpResponseError as e:
        msg = getattr(e, "message", str(e))
        # Retry with normalized PNG if it looks like a format/content issue
        if "InvalidContent" in msg or "Invalid request" in msg:
            try:
                fixed = _normalize_image_bytes(filename or "image", file_bytes)
                return _analyze(fixed)
            except Exception:
                pass  # fall through to raise original error
        raise RuntimeError(f"Form Recognizer request failed: {msg}") from e

    except ResourceNotFoundError as e:
        raise RuntimeError(
            "Form Recognizer 404 (Resource not found)."
        ) from e
