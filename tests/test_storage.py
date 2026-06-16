import os

from common.storage import FileStore
from models.calculate import CarData

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "cars")


def test_fixture_data_loads_as_car_data():
    store = FileStore(FIXTURES)

    index = store.get_index()
    assert index, "fixture catalog should not be empty"

    for entry in index:
        raw = store.get_car(entry["model_id"])
        assert raw is not None, f"missing metadata for {entry['model_id']}"
        # Every fixture metadata file must validate against the schema the engine consumes.
        CarData(**raw)


def test_unknown_model_returns_none():
    store = FileStore(FIXTURES)
    assert store.get_car("does-not-exist") is None
