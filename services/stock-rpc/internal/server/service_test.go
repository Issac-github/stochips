package server

import (
	"context"
	"testing"
	"time"

	stockv1 "stochips/stock_rpc/gen/stockv1"
	"stochips/stock_rpc/internal/tasks"
)

type recordingExecutor struct {
	taskType string
	request  map[string]string
	done     chan struct{}
}

func (e *recordingExecutor) Run(_ context.Context, taskType string, request map[string]string) (string, error) {
	e.taskType = taskType
	e.request = request
	close(e.done)
	return "ok", nil
}

func TestSubmitFetchRunsTaskAndStoresResult(t *testing.T) {
	executor := &recordingExecutor{done: make(chan struct{})}
	store := tasks.NewMemoryStore()
	service := NewStockService(store, executor, nil)

	reply, err := service.SubmitFetch(context.Background(), &stockv1.FetchRequest{Date: "20260521"})
	if err != nil {
		t.Fatalf("submit fetch: %v", err)
	}
	if reply.GetTaskId() == "" {
		t.Fatal("expected task id")
	}

	select {
	case <-executor.done:
	case <-time.After(time.Second):
		t.Fatal("executor was not called")
	}

	if executor.taskType != "fetch" {
		t.Fatalf("expected fetch task, got %q", executor.taskType)
	}
	if executor.request["date"] != "20260521" {
		t.Fatalf("expected date request, got %v", executor.request)
	}

	status, err := service.GetTask(context.Background(), &stockv1.TaskRequest{TaskId: reply.GetTaskId()})
	if err != nil {
		t.Fatalf("get task: %v", err)
	}
	if status.GetStatus() != string(tasks.StatusSucceeded) {
		t.Fatalf("expected succeeded status, got %q", status.GetStatus())
	}
	if status.GetResult() != "ok" {
		t.Fatalf("expected result, got %q", status.GetResult())
	}
}
