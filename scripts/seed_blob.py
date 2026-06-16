"""Upload the bundled car dataset (``data/cars/``) to Azure Blob Storage.

Usage:
    AzureWebJobsStorage="<connection-string>" python scripts/seed_blob.py
    # or against Azurite:
    AzureWebJobsStorage="UseDevelopmentStorage=true" python scripts/seed_blob.py

Uploads every file under data/cars/ to the ``cars`` container, preserving relative paths so the
blob names match what common.storage.BlobStore expects (e.g. ``tesla-model-3/metadata.json``).
"""

import os
import sys

from azure.storage.blob import BlobServiceClient

CONTAINER = os.environ.get("CARS_CONTAINER", "cars")
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "cars"))


def main() -> int:
    connection_string = os.environ.get("CARS_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")
    if not connection_string:
        print("Set CARS_CONNECTION_STRING or AzureWebJobsStorage to the storage connection string", file=sys.stderr)
        return 1
    print(f"uploading {DATA_DIR} -> container '{CONTAINER}'", file=sys.stderr)

    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(CONTAINER)
    try:
        container.create_container()
    except Exception:
        pass  # already exists

    for root, _dirs, files in os.walk(DATA_DIR):
        for name in files:
            local_path = os.path.join(root, name)
            blob_name = os.path.relpath(local_path, DATA_DIR).replace(os.sep, "/")
            with open(local_path, "rb") as f:
                container.upload_blob(name=blob_name, data=f, overwrite=True)
            print(f"uploaded {blob_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
