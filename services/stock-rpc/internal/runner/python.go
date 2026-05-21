package runner

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"path/filepath"
)

type PythonRunner struct {
	Python   string
	AgentDir string
}

func (r PythonRunner) Command(taskType string, request map[string]string) (string, []string, error) {
	python := r.Python
	if python == "" {
		python = "python"
	}
	agentDir := r.AgentDir
	if agentDir == "" {
		agentDir = "."
	}

	mainPath := filepath.Join(agentDir, "main.py")
	date := request["date"]

	switch taskType {
	case "fetch":
		return python, compactArgs(mainPath, "fetch", date), nil
	case "assess":
		return python, compactArgs(mainPath, "assess", date), nil
	case "assess_ai":
		return python, compactArgs(mainPath, "assess-ai", date), nil
	case "run":
		return python, compactArgs(mainPath, "run", date), nil
	case "agent_run":
		goal := request["goal"]
		if goal == "" {
			return "", nil, errors.New("agent_run requires goal")
		}
		return python, compactArgs(mainPath, "agent", goal, date), nil
	default:
		return "", nil, fmt.Errorf("unsupported task type %q", taskType)
	}
}

func (r PythonRunner) Run(ctx context.Context, taskType string, request map[string]string) (string, error) {
	name, args, err := r.Command(taskType, request)
	if err != nil {
		return "", err
	}

	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Dir = r.AgentDir

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		if stderr.Len() > 0 {
			return stdout.String(), fmt.Errorf("%w: %s", err, stderr.String())
		}
		return stdout.String(), err
	}
	return stdout.String(), nil
}

func compactArgs(values ...string) []string {
	args := make([]string, 0, len(values))
	for _, value := range values {
		if value != "" {
			args = append(args, value)
		}
	}
	return args
}
