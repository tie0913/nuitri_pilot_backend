def test_root_get(testclient):
    r = testclient.get("/")
    assert r.status_code == 200

def test_root_post(testclient):
    r = testclient.post("/")
    assert r.status_code == 200
    j = r.json()
    assert j["success"] is True
    assert j["data"]["code"] == "1234567890"