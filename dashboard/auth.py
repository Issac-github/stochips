"""Feishu OAuth and expiring, process-local browser sessions."""

import base64
from dataclasses import dataclass
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
import os
import secrets
import threading
import time
from urllib.parse import urlencode, urlsplit

import requests

SESSION_COOKIE = "stochips_session"
FLOW_COOKIE = "stochips_oauth"
CALLBACK_PATH = "/api/auth/feishu/callback"
AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"


class AuthError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def read_cookie(header, name):
    try:
        cookies = SimpleCookie(header or "")
        return cookies[name].value if name in cookies else ""
    except CookieError:
        return ""


@dataclass(frozen=True)
class AuthConfig:
    app_id: str = ""
    app_secret: str = ""
    public_url: str = "http://127.0.0.1:8787"
    allowed_tenants: tuple = ()
    allowed_users: tuple = ()

    def __post_init__(self):
        url = urlsplit(self.public_url)
        if (url.scheme not in ("https", "http") or not url.hostname
                or url.username or url.password or url.query or url.fragment
                or url.path not in ("", "/")):
            raise ValueError("DASHBOARD_PUBLIC_URL 必须是完整的网站源地址，不含路径或参数")
        if url.scheme == "http" and url.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("非本机的 DASHBOARD_PUBLIC_URL 必须使用 HTTPS")

    @property
    def configured(self):
        return bool(self.app_id and self.app_secret)

    @property
    def origin(self):
        return self.public_url.rstrip("/")

    @property
    def callback_url(self):
        return self.origin + CALLBACK_PATH

    @property
    def secure(self):
        return self.public_url.startswith("https://")

    @classmethod
    def from_env(cls):
        def items(name):
            return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())
        return cls(
            app_id=os.getenv("FEISHU_APP_ID", "").strip(),
            app_secret=os.getenv("FEISHU_APP_SECRET", "").strip(),
            public_url=os.getenv("DASHBOARD_PUBLIC_URL", "http://127.0.0.1:8787").strip(),
            allowed_tenants=items("FEISHU_ALLOWED_TENANT_KEYS"),
            allowed_users=items("FEISHU_ALLOWED_OPEN_IDS"),
        )


class FeishuAuth:
    FLOW_TTL = 300
    SESSION_TTL = 3600

    def __init__(self, config, http=requests, clock=time.time):
        self.config = config
        self.http = http
        self.clock = clock
        self.lock = threading.Lock()
        self.flows = {}
        self.sessions = {}

    def cookie(self, name, value, max_age):
        cookie = SimpleCookie()
        cookie[name] = value
        cookie[name]["path"] = "/api/auth/feishu" if name == FLOW_COOKIE else "/"
        cookie[name]["httponly"] = True
        cookie[name]["samesite"] = "Lax"
        cookie[name]["max-age"] = max_age
        if self.config.secure:
            cookie[name]["secure"] = True
        return cookie.output(header="").strip()

    def _prune(self):
        now = self.clock()
        for store in (self.flows, self.sessions):
            for key in [key for key, value in store.items() if value["expires_at"] <= now]:
                del store[key]

    def start(self, cookie_header=""):
        if not self.config.configured:
            raise AuthError("not_configured")
        state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        with self.lock:
            self._prune()
            previous = read_cookie(cookie_header, FLOW_COOKIE)
            for key in [key for key, flow in self.flows.items() if flow["nonce"] == digest(previous)]:
                del self.flows[key]
            if len(self.flows) >= 1024:
                raise AuthError("busy")
            self.flows[digest(state)] = {
                "nonce": digest(nonce), "verifier": verifier,
                "expires_at": self.clock() + self.FLOW_TTL,
            }
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        params = {
            "client_id": self.config.app_id, "response_type": "code",
            "redirect_uri": self.config.callback_url, "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        }
        return AUTHORIZE_URL + "?" + urlencode(params), self.cookie(FLOW_COOKIE, nonce, self.FLOW_TTL)

    def callback(self, params, cookie_header):
        state = params.get("state", [])
        if len(state) != 1:
            raise AuthError("invalid_state")
        nonce = read_cookie(cookie_header, FLOW_COOKIE)
        with self.lock:
            self._prune()
            flow = self.flows.get(digest(state[0]))
            if not nonce or not flow or not hmac.compare_digest(flow["nonce"], digest(nonce)):
                raise AuthError("invalid_state")
            del self.flows[digest(state[0])]
        if params.get("error"):
            raise AuthError("access_denied")
        codes = params.get("code", [])
        if len(codes) != 1 or not codes[0]:
            raise AuthError("invalid_code")
        try:
            response = self.http.post(TOKEN_URL, json={
                "grant_type": "authorization_code", "client_id": self.config.app_id,
                "client_secret": self.config.app_secret, "code": codes[0],
                "redirect_uri": self.config.callback_url, "code_verifier": flow["verifier"],
            }, timeout=10, allow_redirects=False)
            response.raise_for_status()
            token = response.json()
            if not isinstance(token, dict) or str(token.get("code", 0)) != "0" or not isinstance(token.get("access_token"), str) or not token["access_token"]:
                raise AuthError("upstream_error")
            response = self.http.get(USER_INFO_URL, headers={
                "Authorization": "Bearer " + token["access_token"],
            }, timeout=10, allow_redirects=False)
            response.raise_for_status()
            info = response.json()
            if not isinstance(info, dict) or str(info.get("code")) != "0":
                raise AuthError("upstream_error")
            user = info.get("data")
            if not isinstance(user, dict) or not isinstance(user.get("open_id"), str) or not user["open_id"]:
                raise AuthError("upstream_error")
            lifetime = min(self.SESSION_TTL, int(token["expires_in"]))
            if lifetime <= 0:
                raise AuthError("upstream_error")
        except (requests.RequestException, ValueError, TypeError, KeyError):
            raise AuthError("upstream_error") from None
        if self.config.allowed_tenants and user.get("tenant_key") not in self.config.allowed_tenants:
            raise AuthError("forbidden")
        if self.config.allowed_users and user["open_id"] not in self.config.allowed_users:
            raise AuthError("forbidden")
        safe_user = {key: user.get(key, "") for key in ("open_id", "name", "tenant_key")}
        if not all(isinstance(value, str) for value in safe_user.values()):
            raise AuthError("upstream_error")
        session_id = secrets.token_urlsafe(32)
        with self.lock:
            self._prune()
            if len(self.sessions) >= 4096:
                raise AuthError("busy")
            self.sessions.pop(digest(read_cookie(cookie_header, SESSION_COOKIE)), None)
            self.sessions[digest(session_id)] = {
                "user": safe_user, "csrf_token": secrets.token_urlsafe(32),
                "expires_at": self.clock() + lifetime,
            }
        return self.cookie(SESSION_COOKIE, session_id, lifetime)

    def session(self, cookie_header):
        with self.lock:
            self._prune()
            return self.sessions.get(digest(read_cookie(cookie_header, SESSION_COOKIE)))

    def logout(self, cookie_header, origin, csrf_token):
        session = self.session(cookie_header)
        if not session:
            raise AuthError("unauthorized")
        if origin != self.config.origin or not hmac.compare_digest(session["csrf_token"], csrf_token):
            raise AuthError("forbidden")
        with self.lock:
            self.sessions.pop(digest(read_cookie(cookie_header, SESSION_COOKIE)), None)
        return self.cookie(SESSION_COOKIE, "", 0)
