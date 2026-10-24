# Feishu login integration notes

- Use a separate StoChips custom app. The user selected a new app rather than existing Hermes.
- App created in the signed-in Feishu organization: app id `cli_aa56fa290af85cb7`. Security Settings currently contains only the local dev callback `http://127.0.0.1:5174/api/auth/feishu/callback`; production callback depends on deployment domain.
- OAuth endpoints from Feishu Open Platform docs: authorization `https://accounts.feishu.cn/open-apis/authen/v1/authorize`; v2 user access token `https://open.feishu.cn/open-apis/authen/v2/oauth/token`; user identity `https://open.feishu.cn/open-apis/authen/v1/user_info`.
- Authorization code docs: https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code
- Token exchange docs: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/authentication-management/access-token/get-user-access-token-v3
- Use only basic identity; no contact-list, message, phone or email access. Request no extra scopes in authorization. Exchange token server-side and discard it after user-info lookup.
- Security model: one-use OAuth state tied to HttpOnly flow cookie, S256 PKCE, fixed callback URL, provider redirects disabled, opaque server-side session in HttpOnly SameSite cookie, Secure on HTTPS, one-hour/provider-token expiry, exact Origin and CSRF token on logout. Never trust Host for redirect building or log callback query strings.
- Process-local sessions deliberately fail closed after restart and require a single dashboard process/sticky routing. Missing credentials leaves the sign-in page visible and all report APIs denied.
- Production App Secret must be entered directly into an untracked server environment file; don't copy it into Git, shell history, logs or browser-visible source.
