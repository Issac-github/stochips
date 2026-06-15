# stock_rpc

Go gRPC gateway for the stock agent.

This is the first-stage split:

- Go owns the external gRPC API, in-memory task status, and background task dispatch.
- Python still owns stock fetching, storage, risk assessment, AI analysis, and business table writes.
- The gateway executes the existing `agent/main.py` commands instead of reimplementing business logic.

## Generate gRPC Code

```bash
cd services/stock-rpc
protoc -I proto \
  --go_out=. --go_opt=module=stochips/stock_rpc \
  --go-grpc_out=. --go-grpc_opt=module=stochips/stock_rpc \
  proto/stock.proto
```

## Run Locally

```bash
cd services/stock-rpc
STOCK_RPC_AGENT_DIR=../agent go run ./cmd/stock-rpc
```

The service listens on `:50051` by default.

## Docker Compose

```bash
# from repo root
docker compose up -d --build stock_rpc
```

The compose service exposes `${STOCK_RPC_PORT:-50051}:50051`.
