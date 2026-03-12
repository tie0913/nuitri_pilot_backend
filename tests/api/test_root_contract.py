def test_root_post_contract(testclient):
    r = testclient.post("/")
    assert r.status_code == 200
    j = r.json()

    assert j["success"] is True
    assert j["bizCode"] == 0
    assert j["message"] == ""
    assert j["data"]["code"] == "1234567890"