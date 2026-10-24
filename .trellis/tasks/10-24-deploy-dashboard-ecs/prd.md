# Deploy StoChips dashboard to ECS

## Goal
Deploy the existing dashboard to the running ECS instance at `192.0.2.10` and configure Alibaba Cloud inbound TCP port `8787` so the user can verify the public page.

## Requirements
- Package dashboard as a dedicated Docker Compose service on the existing `stock_network`, reading the existing MySQL database in read-only mode.
- Publish container port 8787 on the ECS host and bind the Python service to `0.0.0.0` inside its container.
- Add a public inbound TCP 8787 security-group rule with a clear dashboard description.
- Preserve the server's existing `.env`; never overwrite it with the developer machine's `.env`.
- Keep Feishu login fail-closed. No public report data without a session. Because the user has no domain, this is only an HTTP reachability/login-page test; production Feishu login awaits HTTPS domain, app secret, and Feishu app publication.
- Preserve existing services and persistent MySQL data.

## Acceptance Criteria
- [x] New dashboard container starts and serves the built login page at `http://192.0.2.10:8787/`.
- [x] Unauthenticated report API returns 401.
- [x] ECS security group permits TCP 8787 from public IPv4.
- [x] Existing containers and database volume remain intact; Compose reports MySQL healthy.
- [x] Deployment and rollback commands are documented.

## Blocking Constraint
Resolved: the Aliyun Workbench session was available, so deployment was performed there without transferring or changing the server `.env`.

## Technical Notes
- Existing server: ECS instance `i-example`, Guangzhou, public IP `192.0.2.10`, security group `sg-example`.
- Existing repository synchronization script deploys `.env`; do not use it as-is because local auth config differs from production and contains local secrets.
- Container image includes both `services/agent` modules and `dashboard/dist`; the ECS build reuses the already-installed `stochips-stock_agent:latest` runtime and its Python dependencies.
- No production domain is available. Public HTTPS/Feishu OAuth activation is out of scope until a domain exists.
