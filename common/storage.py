"""Car-database access layer.

Two backends implement the same interface:

* ``FileStore`` reads the dataset from a local directory (bundled seed data, or anything pointed to
  by the ``CARS_DATA_DIR`` env var). Used for local development and tests.
* ``BlobStore`` reads from Azure Blob Storage, caching each blob to a local temp directory so
  repeated requests don't re-download. This is the production source.

Layout (both backends):

    <root>/index.json                       # catalog: [{model_id, make, model, type, photo}]
    <root>/<model_id>/metadata.json         # CarData fields for one model
    <root>/<model_id>/photo.jpg             # optional stock photo

``get_store()`` picks a backend: ``CARS_DATA_DIR`` -> FileStore; else, if ``USE_BLOB`` is truthy and
``AzureWebJobsStorage`` is set -> BlobStore (the production path); otherwise a local FileStore over
``data/cars`` (a git-ignored working copy you populate with the importers, empty on a fresh clone).
No car data lives in git — the dataset lives in Blob Storage (uploaded with scripts/seed_blob.py).
Tests use their own committed fixtures under tests/fixtures/cars.
"""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

CONTAINER = os.environ.get("CARS_CONTAINER", "cars")
# Local working copy (git-ignored); empty on a fresh clone. Production uses Blob instead.
_BUNDLED_DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "cars"))


class FileStore:
    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)

    def get_index(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.root, "index.json")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def get_car(self, model_id: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.root, model_id, "metadata.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def get_photo(self, model_id: str) -> Optional[bytes]:
        path = os.path.join(self.root, model_id, "photo.jpg")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()


class BlobStore:
    def __init__(self, connection_string: str, container: str = CONTAINER) -> None:
        from azure.storage.blob import BlobServiceClient

        self._service = BlobServiceClient.from_connection_string(connection_string)
        self._container = container
        self._cache_dir = os.path.join(tempfile.gettempdir(), "evcc_cars_cache")
        os.makedirs(self._cache_dir, exist_ok=True)

    def _download(self, name: str) -> Optional[str]:
        local = os.path.join(self._cache_dir, name.replace("/", "__"))
        if os.path.exists(local):
            return local
        client = self._service.get_blob_client(self._container, name)
        try:
            data = client.download_blob().readall()
        except Exception:
            return None
        with open(local, "wb") as f:
            f.write(data)
        return local

    def get_index(self) -> List[Dict[str, Any]]:
        # index.json is mutable (changes when cars are added), so always fetch it fresh instead of
        # serving a stale disk-cached copy. Per-car metadata/photos stay cached (immutable by id).
        try:
            data = self._service.get_blob_client(self._container, "index.json").download_blob().readall()
        except Exception:
            return []
        return json.loads(data)

    def get_car(self, model_id: str) -> Optional[Dict[str, Any]]:
        local = self._download(f"{model_id}/metadata.json")
        if local is None:
            return None
        with open(local, encoding="utf-8") as f:
            return json.load(f)

    def get_photo(self, model_id: str) -> Optional[bytes]:
        local = self._download(f"{model_id}/photo.jpg")
        if local is None:
            return None
        with open(local, "rb") as f:
            return f.read()


def get_store():
    data_dir = os.environ.get("CARS_DATA_DIR")
    if data_dir:
        return FileStore(data_dir)

    # Use a dedicated CARS_CONNECTION_STRING if the car-data container lives in a different
    # storage account than the Functions runtime account; else fall back to AzureWebJobsStorage.
    connection_string = os.environ.get("CARS_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")
    if connection_string and _truthy(os.environ.get("USE_BLOB")):
        return BlobStore(connection_string)

    return FileStore(_BUNDLED_DATA_DIR)


def _truthy(value: Optional[str]) -> bool:
    return value is not None and value.strip().lower() in ("1", "true", "yes", "on")
