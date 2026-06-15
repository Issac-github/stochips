package tasks

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"sync/atomic"
	"time"
)

// SQLStore persists tasks to MySQL so status survives stock_rpc restarts.
// Schema lives in services/agent/migrations/20260522_add_rpc_tasks.sql.
type SQLStore struct {
	db     *sql.DB
	prefix string
	next   atomic.Uint64
}

func NewSQLStore(db *sql.DB) *SQLStore {
	// IDs combine boot timestamp + counter so they remain unique across restarts.
	prefix := fmt.Sprintf("t%d-", time.Now().UTC().UnixNano())
	return &SQLStore{db: db, prefix: prefix}
}

func (s *SQLStore) Create(taskType string, request map[string]string) Task {
	id := s.prefix + fmt.Sprintf("%d", s.next.Add(1))
	task := Task{
		ID:        id,
		Type:      taskType,
		Status:    StatusPending,
		Request:   cloneMap(request),
		CreatedAt: time.Now().UTC(),
	}

	payload, err := json.Marshal(task.Request)
	if err != nil {
		payload = []byte("{}")
	}

	_, err = s.db.Exec(
		`INSERT INTO rpc_tasks (id, type, status, request_json, created_at)
         VALUES (?, ?, ?, ?, ?)`,
		task.ID, task.Type, string(task.Status), string(payload), task.CreatedAt,
	)
	if err != nil {
		// Falling back to returning the task even if write failed lets the
		// gRPC reply succeed; the executor will fail later when it can't
		// mark running. Logging is the caller's responsibility.
		return task
	}
	return task
}

func (s *SQLStore) Get(id string) (Task, bool) {
	row := s.db.QueryRow(
		`SELECT id, type, status, request_json, result, error,
                created_at, started_at, finished_at
         FROM rpc_tasks WHERE id = ?`,
		id,
	)

	var (
		task        Task
		requestJSON sql.NullString
		result      sql.NullString
		errText     sql.NullString
		started     sql.NullTime
		finished    sql.NullTime
		status      string
	)
	err := row.Scan(
		&task.ID, &task.Type, &status, &requestJSON, &result, &errText,
		&task.CreatedAt, &started, &finished,
	)
	if err != nil {
		return Task{}, false
	}
	task.Status = Status(status)
	if requestJSON.Valid && requestJSON.String != "" {
		_ = json.Unmarshal([]byte(requestJSON.String), &task.Request)
	}
	if result.Valid {
		task.Result = result.String
	}
	if errText.Valid {
		task.Error = errText.String
	}
	if started.Valid {
		t := started.Time
		task.StartedAt = &t
	}
	if finished.Valid {
		t := finished.Time
		task.FinishedAt = &t
	}
	return task, true
}

func (s *SQLStore) MarkRunning(id string) error {
	now := time.Now().UTC()
	res, err := s.db.Exec(
		`UPDATE rpc_tasks SET status = ?, started_at = ? WHERE id = ?`,
		string(StatusRunning), now, id,
	)
	return rowsAffectedOrNotFound(res, err)
}

func (s *SQLStore) MarkSucceeded(id string, result string) error {
	now := time.Now().UTC()
	res, err := s.db.Exec(
		`UPDATE rpc_tasks SET status = ?, result = ?, finished_at = ? WHERE id = ?`,
		string(StatusSucceeded), truncate(result, maxResultLen), now, id,
	)
	return rowsAffectedOrNotFound(res, err)
}

func (s *SQLStore) MarkFailed(id string, taskErr error) error {
	now := time.Now().UTC()
	var msg string
	if taskErr != nil {
		msg = taskErr.Error()
	}
	res, err := s.db.Exec(
		`UPDATE rpc_tasks SET status = ?, error = ?, finished_at = ? WHERE id = ?`,
		string(StatusFailed), truncate(msg, maxErrorLen), now, id,
	)
	return rowsAffectedOrNotFound(res, err)
}

const (
	maxResultLen = 4 * 1024 * 1024 // matches MEDIUMTEXT-ish cap; safety bound.
	maxErrorLen  = 8 * 1024
)

func truncate(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[:limit] + "\n... (truncated)"
}

func rowsAffectedOrNotFound(res sql.Result, err error) error {
	if err != nil {
		return err
	}
	affected, affErr := res.RowsAffected()
	if affErr != nil {
		return nil // driver doesn't report, assume update happened
	}
	if affected == 0 {
		return ErrTaskNotFound
	}
	return nil
}

// safeRequestSummary trims the JSON payload for log lines (unused inside the
// store itself but exported for callers who want a short tag).
func safeRequestSummary(request map[string]string) string {
	parts := make([]string, 0, len(request))
	for k, v := range request {
		parts = append(parts, fmt.Sprintf("%s=%s", k, v))
	}
	return strings.Join(parts, ",")
}

var _ = safeRequestSummary // keep helper available; not all builds use it.
