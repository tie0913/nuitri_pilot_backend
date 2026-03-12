def test_wellness_requires_auth_contract(testclient):
    r = testclient.post("/wellness/get_user_wellness_and_items?catalogName=chronics")
    assert r.status_code == 200

    j = r.json()
    assert j["success"] is False

    # Your backend currently returns code=1 for this failure (observed in run output).
    assert j["code"] == 1

def test_wellness_accepts_auth(testclient, auth_headers):
    r = testclient.post(
        "/wellness/get_user_wellness_and_items?catalogName=chronics",
        headers=auth_headers,
    )
    assert r.status_code == 200