package main

import (
	"log"
	"net"
	"os"

	stockv1 "stochips/stock_rpc/gen/stockv1"
	"stochips/stock_rpc/internal/query"
	"stochips/stock_rpc/internal/runner"
	"stochips/stock_rpc/internal/server"
	"stochips/stock_rpc/internal/tasks"

	"google.golang.org/grpc"
)

func main() {
	addr := env("STOCK_RPC_ADDR", ":50051")
	agentDir := env("STOCK_RPC_AGENT_DIR", "..")
	pythonBin := env("PYTHON_BIN", "python")
	databaseURL := os.Getenv("DATABASE_URL")

	listener, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("listen %s: %v", addr, err)
	}

	grpcServer := grpc.NewServer()
	var queries *query.Repository
	if databaseURL != "" {
		var err error
		queries, err = query.NewRepository(databaseURL)
		if err != nil {
			log.Fatalf("init query repository: %v", err)
		}
		defer queries.Close()
	}
	stockv1.RegisterStockServiceServer(
		grpcServer,
		server.NewStockService(
			tasks.NewMemoryStore(),
			runner.PythonRunner{Python: pythonBin, AgentDir: agentDir},
			queries,
		),
	)

	log.Printf("stock_rpc listening on %s, agent_dir=%s", addr, agentDir)
	if err := grpcServer.Serve(listener); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

func env(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
