# function_app/ingest_trigger/__init__.py
import sys
sys.stdout.reconfigure(encoding="utf-8")

import logging
import azure.functions as func

from .document_intelligence import extract_text_from_document
from .ingestion_pipeline import process_and_index_text


def main(inputBlob: func.InputStream):
    logging.info(f"--- Blob Triggered: {inputBlob.name} ({inputBlob.length} bytes)")

    raw_bytes = inputBlob.read()
    filename = inputBlob.name.split("/")[-1]

    try:
        extracted_text = extract_text_from_document(raw_bytes, filename)

        if not extracted_text.strip():
            logging.warning("No text extracted from document.")
            return

        process_and_index_text(text=extracted_text, filename=filename)
        logging.info("Document successfully processed and indexed.")

    except Exception as e:
        logging.exception(f"Ingestion failed: {str(e)}")
