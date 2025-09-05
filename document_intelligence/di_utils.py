"""
Utility functions for Document Intelligence processing + Blob I/O.
"""
import io
from PIL import Image
import re
import mimetypes
from typing import Optional
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient, ContentSettings, ContainerClient
from azure.ai.formrecognizer import DocumentAnalysisClient

SUPPORTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".txt"}



def _normalize_image_bytes(name: str, data: bytes) -> bytes:
    """
    Best-effort: open image bytes and re-encode as clean RGB PNG.
    Fixes cases where the extension is PNG but the actual encoding is WebP/HEIC/etc.,
    or where alpha/ICC profiles cause issues.
    """
    with Image.open(io.BytesIO(data)) as im:
        # Convert to a safe mode (RGB). If it's bilevel/LA/CMYK, normalize.
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="PNG")  # lossless clean PNG
        return out.getvalue()


def get_blob_container(connection_string: str, container_name: str) -> ContainerClient:
    svc = BlobServiceClient.from_connection_string(connection_string)
    return svc.get_container_client(container_name)


def ensure_container(container: ContainerClient) -> None:
    try:
        container.create_container()
    except Exception:
        pass  # already exists or not allowed


def guess_content_type(name: str) -> Optional[str]:
    ctype, _ = mimetypes.guess_type(name)
    return ctype


def clean_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t\f\v]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = "".join(ch for ch in t if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return t.strip()


def make_di_client(endpoint: str, key: str) -> DocumentAnalysisClient:
    return DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))


def extract_text_with_document_intelligence(
    di_client: DocumentAnalysisClient, data: bytes, content_type: Optional[str]
) -> str:
    """
    Run the prebuilt 'read' model (supports printed + handwriting).
    If DI rejects the image bytes as invalid/unsupported, transcode to clean PNG and retry once.
    """
    def _analyze(raw: bytes) -> str:
        poller = di_client.begin_analyze_document(
            model_id="prebuilt-read",
            document=raw
        )
        result = poller.result()
        if getattr(result, "content", None):
            return result.content
        lines = []
        for page in (result.pages or []):
            for line in (page.lines or []):
                lines.append(line.content)
        return "\n".join(lines)

    # first attempt
    try:
        return _analyze(data)
    except Exception as e:
        msg = str(e)
        # Only try to normalize if this looks like a content/format issue
        if "InvalidContent" in msg or "Invalid request" in msg:
            try:
                fixed = _normalize_image_bytes("image", data)
                return _analyze(fixed)
            except Exception:
                # fall through to raise the original error below
                pass
        raise



def upload_text(container: ContainerClient, name: str, text: str) -> None:
    cs = ContentSettings(content_type="text/plain; charset=utf-8")
    container.upload_blob(
        name=name,
        data=text.encode("utf-8"),
        overwrite=True,
        content_settings=cs,
    )
