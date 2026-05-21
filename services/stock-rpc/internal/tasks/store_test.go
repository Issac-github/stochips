package tasks

import (
	"errors"
	"testing"
)

func TestMemoryStoreCreatesAndCompletesTask(t *testing.T) {
	store := NewMemoryStore()

	task := store.Create("fetch", map[string]string{"date": "2026-05-21"})
	if task.ID == "" {
		t.Fatal("expected task id")
	}
	if task.Type != "fetch" {
		t.Fatalf("expected fetch task, got %q", task.Type)
	}
	if task.Status != StatusPending {
		t.Fatalf("expected pending status, got %q", task.Status)
	}

	if err := store.MarkRunning(task.ID); err != nil {
		t.Fatalf("mark running: %v", err)
	}
	if err := store.MarkSucceeded(task.ID, "ok"); err != nil {
		t.Fatalf("mark succeeded: %v", err)
	}

	got, ok := store.Get(task.ID)
	if !ok {
		t.Fatal("expected task to be retrievable")
	}
	if got.Status != StatusSucceeded {
		t.Fatalf("expected succeeded status, got %q", got.Status)
	}
	if got.Result != "ok" {
		t.Fatalf("expected result to be stored, got %q", got.Result)
	}
	if got.StartedAt == nil {
		t.Fatal("expected started timestamp")
	}
	if got.FinishedAt == nil {
		t.Fatal("expected finished timestamp")
	}
}

func TestMemoryStoreFailsUnknownTask(t *testing.T) {
	store := NewMemoryStore()

	err := store.MarkFailed("missing", errors.New("boom"))
	if !errors.Is(err, ErrTaskNotFound) {
		t.Fatalf("expected ErrTaskNotFound, got %v", err)
	}
}
