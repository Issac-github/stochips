package main

import (
	"database/sql"
	"log"
	"net"
	"os"
	"time"

	stockv1 "stochips/stock_rpc/gen/stockv1"
	"stochips/stock_rpc/internal/query"
	"stochips/stock_rpc/internal/runner"
	"stochips/stock_rpc/internal/server"
	"stochips/stock_rpc/internal/tasks"

	_ "github.com/go-sql-driver/mysql"
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
	var store tasks.Store = tasks.NewMemoryStore()

	if databaseURL != "" {
		queries, err = query.NewRepository(databaseURL)
		if err != nil {
			log.Fatalf("init query repository: %v", err)
		}
		defer queries.Close()

		taskDB, err := openTaskDB(databaseURL)
		if err != nil {
			log.Printf("WARN: SQL task store unavailable, falling back to memory: %v", err)
		} else {
			store = tasks.NewSQLStore(taskDB)
			log.Printf("task store: mysql")
			defer taskDB.Close()
		}
	} else {
		log.Printf("DATABASE_URL not set; running with in-memory task store and no query repository")
	}

	stockv1.RegisterStockServiceServer(
		grpcServer,
		server.NewStockService(
			store,
			runner.PythonRunner{Python: pythonBin, AgentDir: agentDir},
			queries,
		),
	)

	log.Printf("stock_rpc listening on %s, agent_dir=%s", addr, agentDir)
	if err := grpcServer.Serve(listener); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

func openTaskDB(databaseURL string) (*sql.DB, error) {
	dsn, err := query.MySQLURLToDSN(databaseURL)
	if err != nil {
		return nil, err
	}
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(8)
	db.SetMaxIdleConns(4)
	db.SetConnMaxLifetime(30 * time.Minute)
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func env(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
