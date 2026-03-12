import pytest

pytestmark = pytest.mark.integration


def test_mongo_insert_and_find_real(is_docker_available):
    if not is_docker_available:
        pytest.skip("Docker not available; skipping Mongo integration test")

    from testcontainers.mongodb import MongoDbContainer
    from pymongo import MongoClient

    with MongoDbContainer("mongo:7") as mongo:
        uri = mongo.get_connection_url()
        client = MongoClient(uri)
        db = client["nuitripilot_test"]
        col = db["smoke"]

        col.insert_one({"name": "boss", "v": 1})
        doc = col.find_one({"name": "boss"})

        assert doc is not None
        assert doc["v"] == 1
