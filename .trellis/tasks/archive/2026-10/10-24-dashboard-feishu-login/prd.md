# Dashboard Feishu login

## Goal
Add Feishu OAuth login to the existing report dashboard, with server-enforced report access and a clear login/logout UI.

## Known facts
- Dashboard currently exposes read-only reports without authentication via Python stdlib HTTP.
- User provided https://open.feishu.cn/app and selected a new independent StoChips custom app. Created StoChips custom app `cli_aa56fa290af85cb7` in 用户803416的组织; registered localhost development callback `http://127.0.0.1:5174/api/auth/feishu/callback`. Production domain and secret are not yet configured. Do not use or alter Hermes.
- `.env.example` has existing staged user changes; preserve them.

## Requirements
- OAuth authorization-code flow; server exchanges code, tokens never reach browser storage.
- One-use random state bound to browser cookie, short expiry; PKCE if supported by official endpoint.
- Server-side random session with expiry, HttpOnly/SameSite cookie, Secure on HTTPS, logout invalidation, CSRF-protected POST logout.
- Auth enforced on /api/dates and /api/report before DB access; /api/auth/session provides config status and sanitized identity.
- Default fail closed when credentials missing; show actionable configuration UI, no silent anonymous mode.
- Enterprise custom app available range controls users; optional tenant/open_id allowlists for narrower access.
- Keep public base URL explicit; callback is fixed /api/auth/feishu/callback. Production HTTPS, local loopback HTTP supported.
- Login page, user name and logout, reauthentication after API 401.
- Environment config + setup documentation, no real secrets in Git.

## Acceptance criteria
- [x] Login redirect/state/callback/session/logout and upstream rejection/tenant mismatch tested without live Feishu.
- [x] Unauthorized report APIs return 401 before any database query.
- [x] Frontend login/config/error/session expiry states implemented; existing report behavior preserved after auth.
- [x] lint/typecheck/build and Python tests pass.

## Out of scope
- Requesting contact list, messages, phone/email, offline access; changing existing bot configuration; external deployment without selected app/domain.

## Remaining external setup
- Set `FEISHU_APP_ID=cli_aa56fa290af85cb7`, copy the generated `FEISHU_APP_SECRET` directly into the server's untracked `.env`, and set `DASHBOARD_PUBLIC_URL`. For production, register the matching HTTPS callback URL and publish the custom app version. The user has not yet supplied a production domain.
