def test_jwt_token_roundtrip():
    from src.auth.token import create_token, decode_token

    token = create_token("user-abc")
    status, payload = decode_token(token)

    assert status == 0
    assert payload["text"] == "user-abc"