"""OAuth flow and session security using a fake Feishu server."""

from urllib.parse import parse_qs, urlsplit

import pytest

from auth import AuthConfig, AuthError, FeishuAuth


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class Feishu:
    def __init__(self, user=None):
        self.user = user or {"open_id": "ou_1", "name": "小明", "tenant_key": "tenant_1"}
        self.token_request = None

    def post(self, _url, **kwargs):
        self.token_request = kwargs["json"]
        return Response({"code": 0, "access_token": "private-token", "expires_in": 7200})

    def get(self, _url, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer private-token"
        return Response({"code": 0, "data": self.user})


def config(**kwargs):
    return AuthConfig(app_id="app", app_secret="secret", **kwargs)


def test_login_state_pkce_session_and_one_time_callback():
    provider = Feishu()
    auth = FeishuAuth(config(), http=provider)
    location, flow_cookie = auth.start()
    query = parse_qs(urlsplit(location).query)
    assert query["client_id"] == ["app"]
    assert query["redirect_uri"] == ["http://127.0.0.1:8787/api/auth/feishu/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert "state" in query
    cookie = flow_cookie.split(";", 1)[0]
    session_cookie = auth.callback({"state": query["state"], "code": ["one-use"]}, cookie)
    assert "HttpOnly" in session_cookie and "SameSite=Lax" in session_cookie
    assert provider.token_request["code_verifier"]
    session_header = session_cookie.split(";", 1)[0]
    session = auth.session(session_header)
    assert session["user"]["name"] == "小明"
    assert "private-token" not in repr(session)
    with pytest.raises(AuthError, match="invalid_state"):
        auth.callback({"state": query["state"], "code": ["replay"]}, cookie)
    assert auth.logout(session_header, auth.config.origin, session["csrf_token"])
    assert auth.session(session_header) is None


def test_state_must_be_bound_to_flow_cookie_and_allowlist_is_enforced():
    auth = FeishuAuth(config(allowed_tenants=("tenant_2",)), http=Feishu())
    location, flow_cookie = auth.start()
    state = parse_qs(urlsplit(location).query)["state"]
    with pytest.raises(AuthError, match="invalid_state"):
        auth.callback({"state": state, "code": ["x"]}, "stochips_oauth=wrong")
    with pytest.raises(AuthError, match="forbidden"):
        auth.callback({"state": state, "code": ["x"]}, flow_cookie.split(";", 1)[0])


def test_expired_flow_and_logout_require_origin_and_csrf():
    now = [1000]
    auth = FeishuAuth(config(), http=Feishu(), clock=lambda: now[0])
    location, flow_cookie = auth.start()
    state = parse_qs(urlsplit(location).query)["state"]
    now[0] += auth.FLOW_TTL
    with pytest.raises(AuthError, match="invalid_state"):
        auth.callback({"state": state, "code": ["x"]}, flow_cookie)
    location, flow_cookie = auth.start()
    state = parse_qs(urlsplit(location).query)["state"]
    cookie = auth.callback({"state": state, "code": ["x"]}, flow_cookie)
    header = cookie.split(";", 1)[0]
    session = auth.session(header)
    with pytest.raises(AuthError, match="forbidden"):
        auth.logout(header, "https://evil.example", session["csrf_token"])
    with pytest.raises(AuthError, match="forbidden"):
        auth.logout(header, auth.config.origin, "wrong")


def test_redirect_and_plain_http_public_url_constraints():
    with pytest.raises(ValueError):
        config(public_url="http://dashboard.example.com")
    with pytest.raises(ValueError):
        config(public_url="https://dashboard.example.com/other")
