#!/usr/bin/env python3
"""
Debug-enabled main:
- Loads .env from the script directory (so cwd doesn't matter)
- Echoes key config (masked)
- Lists first few blobs before processing
- Exits early with clear messages if nothing is found
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from di_utils import (
    SUPPORTED_EXTS,
    get_blob_container, ensure_container,
    guess_content_type, clean_text,
    make_di_client, extract_text_with_document_intelligence,
    upload_text,
)

def _mask_conn_str(cs: str) -> str:
    if not cs:
        return ""
    # keep account name visible, mask keys
    parts = cs.split(";")
    masked = []
    for p in parts:
        if p.startswith("AccountKey=") or p.startswith("SharedAccessSignature="):
            k, _, v = p.partition("=")
            masked.append(f"{k}=***masked***")
        else:
            masked.append(p)
    return ";".join(masked)

def _get_env(name: str) -> str:
    v = os.getenv(name, "")
    if not v:
        raise SystemExit(f"[config] Missing env var: {name}")
    return v

def _list_head(items, n=5) -> List[str]:
    head = []
    for i, it in enumerate(items):
        if i >= n:
            break
        head.append(it)
    return head

def run():
    # Ensure we load .env from the script directory,
    # not just the current working directory.
    script_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=script_dir / ".env")

    # --- Required env vars ---
    src_conn = _get_env("SRC_BLOB_CONNECTION_STRING")
    src_container_name = _get_env("SRC_BLOB_CONTAINER")
    dst_conn = os.getenv("DST_BLOB_CONNECTION_STRING") or src_conn  # fallback to same account
    dst_container_name = _get_env("DST_BLOB_CONTAINER")
    di_endpoint = _get_env("DOCUMENT_INTELLIGENCE_ENDPOINT")
    di_key = _get_env("DOCUMENT_INTELLIGENCE_KEY")

    print("[cfg] Using .env at:", (script_dir / ".env"))
    print("[cfg] SRC_CONTAINER =", src_container_name)
    print("[cfg] DST_CONTAINER =", dst_container_name)
    print("[cfg] SRC_CONN     =", _mask_conn_str(src_conn))
    print("[cfg] DST_CONN     =", _mask_conn_str(dst_conn))
    print("[cfg] DI_ENDPOINT  =", di_endpoint)

    # --- Clients ---
    try:
        src = get_blob_container(src_conn, src_container_name)
        dst = get_blob_container(dst_conn, dst_container_name)
    except Exception as e:
        raise SystemExit(f"[error] Failed to create blob clients: {e}")

    ensure_container(dst)

    # --- Probe blob list first (smoke test) ---
    print("[probe] Listing up to 5 blobs in source container...")
    try:
        names = []
        for i, b in enumerate(src.list_blobs()):
            names.append(b.name)
            if i >= 49:  # collect up to 50 for counting
                break
        if not names:
            raise SystemExit("[probe] No blobs found in the source container. "
                             "Check container name and that files are uploaded.")
        print(f"[probe] Found at least {len(names)} blobs (showing up to 5):")
        for s in _list_head(names, 5):
            print("         -", s)
    except Exception as e:
        raise SystemExit(f"[error] Unable to list blobs: {e}")

    # --- DI client ---
    try:
        di = make_di_client(di_endpoint, di_key)
    except Exception as e:
        raise SystemExit(f"[error] Failed to create Document Intelligence client: {e}")

    # --- Iterate & process ---
    total = written = skipped = 0
    print("[run] Starting processing...")
    try:
        for blob in src.list_blobs():
            name = blob.name
            base, ext = os.path.splitext(name)
            ext = ext.lower()

            if ext not in SUPPORTED_EXTS:
                print(f"[skip] {name} (unsupported ext)")
                skipped += 1
                continue

            print(f"[read] {name}")
            data = src.get_blob_client(name).download_blob().readall()
            total += 1

            if ext == ".txt":
                text = data.decode("utf-8", errors="ignore")
            else:
                ctype = guess_content_type(name) or None
                text = extract_text_with_document_intelligence(di, data, ctype)

            text = clean_text(text)
            if not text:
                print(f"[warn] No text extracted from {name}; skipping output")
                skipped += 1
                continue

            out_name = f"{base}.txt"
            upload_text(dst, out_name, text)
            print(f"[write] {out_name} ({len(text)} chars)")
            written += 1

        print(f"[done] total inputs={total}, written={written}, skipped={skipped}")
    except KeyboardInterrupt:
        print("\n[info] Interrupted by user.")
    except Exception as e:
        raise SystemExit(f"[error] Unhandled error during processing: {e}")

if __name__ == "__main__":
    run()
