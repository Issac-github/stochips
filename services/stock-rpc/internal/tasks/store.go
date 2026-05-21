package tasks

import (
	"errors"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

type Status string

const (
	StatusPending   Status = "pending"
	StatusRunning   Status = "running"
	StatusSucceeded Status = "succeeded"
	StatusFailed    Status = "failed"
)

var ErrTaskNotFound = errors.New("task not found")

type Task struct {
	ID         string
	Type       string
	Status     Status
	Request    map[string]string
	Result     string
	Error      string
	CreatedAt  time.Time
	StartedAt  *time.Time
	FinishedAt *time.Time
}

type MemoryStore struct {
	mu    sync.RWMutex
	next  atomic.Uint64
	tasks map[string]Task
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{tasks: make(map[string]Task)}
}

func (s *MemoryStore) Create(taskType string, request map[string]string) Task {
	id := strconv.FormatUint(s.next.Add(1), 10)
	task := Task{
		ID:        id,
		Type:      taskType,
		Status:    StatusPending,
		Request:   cloneMap(request),
		CreatedAt: time.Now().UTC(),
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	s.tasks[id] = task
	return task
}

func (s *MemoryStore) Get(id string) (Task, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	task, ok := s.tasks[id]
	return task, ok
}

func (s *MemoryStore) MarkRunning(id string) error {
	return s.update(id, func(task *Task, now time.Time) {
		task.Status = StatusRunning
		task.StartedAt = &now
	})
}

func (s *MemoryStore) MarkSucceeded(id string, result string) error {
	return s.update(id, func(task *Task, now time.Time) {
		task.Status = StatusSucceeded
		task.Result = result
		task.FinishedAt = &now
	})
}

func (s *MemoryStore) MarkFailed(id string, err error) error {
	return s.update(id, func(task *Task, now time.Time) {
		task.Status = StatusFailed
		if err != nil {
			task.Error = err.Error()
		}
		task.FinishedAt = &now
	})
}

func (s *MemoryStore) update(id string, apply func(*Task, time.Time)) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	task, ok := s.tasks[id]
	if !ok {
		return ErrTaskNotFound
	}

	now := time.Now().UTC()
	apply(&task, now)
	s.tasks[id] = task
	return nil
}

func cloneMap(src map[string]string) map[string]string {
	dst := make(map[string]string, len(src))
	for key, value := range src {
		dst[key] = value
	}
	return dst
}
